from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import FUEL_BY_DATASET_KEY, SUPPORTED_PRICE_KEYS
from app.integrations.fuel_api import MineturApiClient
from app.repositories.fuels import FuelsRepository
from app.repositories.notifications import NotificationsRepository
from app.repositories.station_prices import StationPricesRepository
from app.repositories.stations import StationsRepository
from app.repositories.sync_runs import SyncRunsRepository
from app.repositories.watchlists import WatchlistsRepository
from app.utils.parsing import clean_text, digits_only, normalize_text, parse_coordinate, parse_dataset_datetime, parse_decimal
from app.utils.timezone import madrid_tz, now_madrid

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PriceSnapshot:
    station_id: str
    fuel_id: int
    price: Decimal
    dataset_timestamp: datetime


class SyncService:
    def __init__(self, session: AsyncSession, client: MineturApiClient) -> None:
        self.session = session
        self.client = client
        self.fuels_repository = FuelsRepository(session)
        self.stations_repository = StationsRepository(session)
        self.station_prices_repository = StationPricesRepository(session)
        self.watchlists_repository = WatchlistsRepository(session)
        self.notifications_repository = NotificationsRepository(session)
        self.sync_runs_repository = SyncRunsRepository(session)

    async def run_sync(self) -> dict[str, int | str]:
        started_at = now_madrid()
        sync_run = await self.sync_runs_repository.create_started(started_at)
        await self.session.commit()

        try:
            await self.fuels_repository.seed_defaults()
            payload = await self.client.fetch_dataset()
            dataset_timestamp, stations_payloads, price_snapshots = self._parse_dataset(payload, observed_at=started_at)
            existing_prices = await self.station_prices_repository.load_current_price_map()
            await self.stations_repository.upsert_many(stations_payloads)

            history_rows: list[dict[str, Any]] = []
            current_rows: list[dict[str, Any]] = []
            drops: list[tuple[str, int, Decimal, Decimal]] = []
            available_keys: list[tuple[str, int]] = []

            for snapshot in price_snapshots.values():
                key = (snapshot.station_id, snapshot.fuel_id)
                available_keys.append(key)
                existing = existing_prices.get(key)
                changed = existing is None or existing.current_price != snapshot.price or not existing.is_available
                last_changed_at = snapshot.dataset_timestamp if changed else existing.last_changed_at

                current_rows.append(
                    {
                        "station_id": snapshot.station_id,
                        "fuel_id": snapshot.fuel_id,
                        "current_price": snapshot.price,
                        "dataset_timestamp": snapshot.dataset_timestamp,
                        "last_seen_at": snapshot.dataset_timestamp,
                        "last_changed_at": last_changed_at,
                        "is_available": True,
                    }
                )

                if existing is None:
                    history_rows.append(
                        {
                            "station_id": snapshot.station_id,
                            "fuel_id": snapshot.fuel_id,
                            "sync_run_id": sync_run.id,
                            "previous_price": None,
                            "new_price": snapshot.price,
                            "dataset_timestamp": snapshot.dataset_timestamp,
                            "observed_at": started_at,
                        }
                    )
                    continue

                if changed:
                    history_rows.append(
                        {
                            "station_id": snapshot.station_id,
                            "fuel_id": snapshot.fuel_id,
                            "sync_run_id": sync_run.id,
                            "previous_price": existing.current_price,
                            "new_price": snapshot.price,
                            "dataset_timestamp": snapshot.dataset_timestamp,
                            "observed_at": started_at,
                        }
                    )
                    if snapshot.price < existing.current_price:
                        drops.append((snapshot.station_id, snapshot.fuel_id, existing.current_price, snapshot.price))

            await self.station_prices_repository.upsert_current_many(current_rows)
            await self.station_prices_repository.mark_missing_unavailable(available_keys, dataset_timestamp)
            await self.station_prices_repository.insert_history_many(history_rows)

            pairs = [(station_id, fuel_id) for station_id, fuel_id, _, _ in drops]
            watchlists_by_pair = await self.watchlists_repository.list_active_for_pairs(pairs)
            notification_rows: list[dict[str, Any]] = []
            for station_id, fuel_id, previous_price, new_price in drops:
                for watchlist in watchlists_by_pair.get((station_id, fuel_id), []):
                    notification_rows.append(
                        {
                            "watchlist_id": watchlist.id,
                            "sync_run_id": sync_run.id,
                            "station_id": station_id,
                            "fuel_id": fuel_id,
                            "previous_price": previous_price,
                            "new_price": new_price,
                            "dataset_timestamp": dataset_timestamp,
                        }
                    )

            await self.notifications_repository.bulk_create_pending(notification_rows)
            await self.sync_runs_repository.mark_success(
                sync_run,
                finished_at=now_madrid(),
                dataset_timestamp=dataset_timestamp,
                stations_received=len(stations_payloads),
                price_rows_received=len(price_snapshots),
                price_rows_changed=len(history_rows),
                price_drops_detected=len(notification_rows),
            )
            await self.session.commit()
            return {
                "sync_run_id": sync_run.id,
                "stations_received": len(stations_payloads),
                "price_rows_received": len(price_snapshots),
                "price_rows_changed": len(history_rows),
                "price_drops_detected": len(notification_rows),
                "dataset_timestamp": dataset_timestamp.isoformat(),
            }
        except Exception as exc:
            logger.exception("Sync failed")
            await self.session.rollback()
            await self.sync_runs_repository.mark_failed(sync_run, finished_at=now_madrid(), error_message=str(exc))
            await self.session.commit()
            raise

    def _parse_dataset(
        self,
        payload: dict[str, Any],
        *,
        observed_at: datetime,
    ) -> tuple[datetime, list[dict[str, Any]], dict[tuple[str, int], PriceSnapshot]]:
        dataset_timestamp = parse_dataset_datetime(str(payload.get("Fecha") or "")) or now_madrid().replace(second=0, microsecond=0)
        dataset_timestamp = dataset_timestamp.replace(tzinfo=madrid_tz()) if dataset_timestamp.tzinfo is None else dataset_timestamp
        raw_stations = payload.get("ListaEESSPrecio") or []

        station_rows: list[dict[str, Any]] = []
        price_snapshots: dict[tuple[str, int], PriceSnapshot] = {}

        for item in raw_stations:
            ideess = clean_text(item.get("IDEESS"))
            if not ideess:
                continue

            postal_code = digits_only(item.get("C.P."))
            if postal_code and len(postal_code) < 5:
                postal_code = postal_code.zfill(5)

            address = clean_text(item.get("Direcci\u00f3n")) or "Direccion no disponible"
            locality = clean_text(item.get("Localidad"))
            municipality = clean_text(item.get("Municipio")) or locality or "Municipio no disponible"
            province = clean_text(item.get("Provincia")) or "Provincia no disponible"
            brand = clean_text(item.get("R\u00f3tulo")) or "Sin rotulo"

            station_rows.append(
                {
                    "ideess": ideess,
                    "postal_code": postal_code,
                    "address": address,
                    "address_normalized": normalize_text(address) or "",
                    "locality": locality,
                    "locality_normalized": normalize_text(locality),
                    "municipality": municipality,
                    "municipality_normalized": normalize_text(municipality) or "",
                    "province": province,
                    "province_normalized": normalize_text(province) or "",
                    "brand": brand,
                    "brand_normalized": normalize_text(brand) or "",
                    "schedule": clean_text(item.get("Horario")),
                    "margin": clean_text(item.get("Margen")),
                    "sale_type": clean_text(item.get("Tipo_x0020_Venta")),
                    "remision": clean_text(item.get("Remisi\u00f3n")),
                    "locality_code": clean_text(item.get("IDMunicipio")),
                    "province_code": clean_text(item.get("IDProvincia")),
                    "autonomous_region_code": clean_text(item.get("IDCCAA")),
                    "latitude": parse_coordinate(item.get("Latitud")),
                    "longitude": parse_coordinate(item.get("Longitud_x0020__x0028_WGS84_x0029_")),
                    "is_active": True,
                    "updated_at": observed_at,
                }
            )

            for price_key in SUPPORTED_PRICE_KEYS:
                fuel_config = FUEL_BY_DATASET_KEY[price_key]
                price_value = parse_decimal(item.get(price_key))
                if price_value is None:
                    continue
                key = (ideess, int(fuel_config["id"]))
                price_snapshots[key] = PriceSnapshot(
                    station_id=ideess,
                    fuel_id=int(fuel_config["id"]),
                    price=price_value,
                    dataset_timestamp=dataset_timestamp,
                )

        deduped_stations = {row["ideess"]: row for row in station_rows}
        return dataset_timestamp, list(deduped_stations.values()), price_snapshots
