from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.notification import NotificationSent
from app.models.station_price import StationPriceCurrent
from app.models.user import User
from app.models.watchlist import UserWatchlist
from app.repositories.watchlists import WatchlistsRepository
from app.services.sync_service import SyncService
from app.utils.formatting import format_notification_message


class FakeClient:
    def __init__(self, payloads):
        self.payloads = iter(payloads)

    async def fetch_dataset(self):
        return next(self.payloads)


def _payload(price: str) -> dict:
    return {
        "Fecha": "25/03/2026 12:30",
        "ListaEESSPrecio": [
            {
                "IDEESS": "12345",
                "C.P.": "30001",
                "Dirección": "Av. Libertad 1",
                "Horario": "L-D: 24H",
                "Latitud": "37,983000",
                "Localidad": "Murcia",
                "Longitud_x0020__x0028_WGS84_x0029_": "-1,128000",
                "Margen": "D",
                "Municipio": "Murcia",
                "Provincia": "Murcia",
                "Remisión": "dm",
                "Rótulo": "Repsol",
                "Tipo_x0020_Venta": "P",
                "IDMunicipio": "399",
                "IDProvincia": "30",
                "IDCCAA": "14",
                "Precio_x0020_Gasoleo_x0020_A": price,
            }
        ],
    }


def _payload_with_decoded_keys(price: str) -> dict:
    return {
        "Fecha": "25/03/2026 12:30",
        "ListaEESSPrecio": [
            {
                "IDEESS": "54321",
                "C.P.": "28001",
                "Dirección": "Calle Alcala 1",
                "Horario": "L-D: 24H",
                "Latitud": "40,420000",
                "Localidad": "Madrid",
                "Longitud (WGS84)": "-3,690000",
                "Margen": "D",
                "Municipio": "Madrid",
                "Provincia": "Madrid",
                "Remisión": "dm",
                "Rótulo": "Cepsa",
                "Tipo Venta": "P",
                "IDMunicipio": "79",
                "IDProvincia": "28",
                "IDCCAA": "13",
                "Precio Gasoleo A": price,
            }
        ],
    }


async def test_sync_detects_price_drop_and_avoids_duplicates(session_factory) -> None:
    async with session_factory() as session:
        service = SyncService(session=session, client=FakeClient([_payload("1,489")]))
        await service.run_sync()

    async with session_factory() as session:
        user = User(telegram_user_id=111, username="tester", first_name="Test", last_name="User")
        session.add(user)
        await session.flush()
        repository = WatchlistsRepository(session)
        watchlist, created = await repository.create_or_reactivate(user.id, "12345", 1)
        assert created is True
        await session.commit()
        assert watchlist.fuel_id == 1

    async with session_factory() as session:
        service = SyncService(session=session, client=FakeClient([_payload("1,459")]))
        result = await service.run_sync()
        assert result["price_drops_detected"] == 1

    async with session_factory() as session:
        notifications = await session.execute(
            select(NotificationSent)
            .options(joinedload(NotificationSent.watchlist))
            .order_by(NotificationSent.id.asc())
        )
        rows = notifications.scalars().all()
        assert len(rows) == 1
        assert rows[0].previous_price == Decimal("1.489")
        assert rows[0].new_price == Decimal("1.459")

    async with session_factory() as session:
        service = SyncService(session=session, client=FakeClient([_payload("1,459")]))
        result = await service.run_sync()
        assert result["price_drops_detected"] == 0

    async with session_factory() as session:
        total_notifications = await session.scalar(select(func.count(NotificationSent.id)))
        assert total_notifications == 1


async def test_sync_accepts_decoded_dataset_field_names(session_factory) -> None:
    async with session_factory() as session:
        service = SyncService(session=session, client=FakeClient([_payload_with_decoded_keys("1,499")]))
        result = await service.run_sync()
        assert result["stations_received"] == 1
        assert result["price_rows_received"] == 1

    async with session_factory() as session:
        total_current_rows = await session.scalar(select(func.count()).select_from(StationPriceCurrent))
        assert total_current_rows == 1


def test_format_notification_message_keeps_naive_dataset_timestamp_as_madrid_time() -> None:
    notification = SimpleNamespace(
        station=SimpleNamespace(brand="SERMUCO", address="POLIGONO LOS PRADOS, 6", municipality="Cieza"),
        fuel=SimpleNamespace(name="Gasoleo A"),
        previous_price=Decimal("1.689"),
        new_price=Decimal("1.649"),
        dataset_timestamp=datetime(2026, 3, 27, 12, 54),
    )

    text = format_notification_message(notification)

    assert "27/03/2026 12:54" in text


def test_format_notification_message_converts_aware_dataset_timestamp_to_madrid_time() -> None:
    notification = SimpleNamespace(
        station=SimpleNamespace(brand="SERMUCO", address="POLIGONO LOS PRADOS, 6", municipality="Cieza"),
        fuel=SimpleNamespace(name="Gasoleo A"),
        previous_price=Decimal("1.689"),
        new_price=Decimal("1.649"),
        dataset_timestamp=datetime(2026, 3, 27, 11, 54, tzinfo=timezone.utc),
    )

    text = format_notification_message(notification)

    assert "27/03/2026 12:54" in text
