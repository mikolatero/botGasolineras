from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from math import cos, radians

from sqlalchemy import Float, Select, and_, bindparam, cast, func, or_, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fuel import Fuel
from app.models.station import Station
from app.models.station_price import StationPriceCurrent
from app.repositories.base import Repository
from app.utils.parsing import normalize_text


def _upsert_statement(session: AsyncSession, payloads: list[dict], table, update_columns: Iterable[str]):
    dialect = session.bind.dialect.name
    if dialect == "mysql":
        stmt = mysql_insert(table).values(payloads)
        updates = {column: stmt.inserted[column] for column in update_columns}
        return stmt.on_duplicate_key_update(**updates)
    if dialect == "sqlite":
        stmt = sqlite_insert(table).values(payloads)
        pk_columns = [column.name for column in table.primary_key.columns]
        updates = {column: stmt.excluded[column] for column in update_columns}
        return stmt.on_conflict_do_update(index_elements=pk_columns, set_=updates)
    raise RuntimeError(f"Unsupported dialect for upsert: {dialect}")


class StationsRepository(Repository):
    async def upsert_many(self, payloads: list[dict]) -> None:
        if not payloads:
            return
        statement = _upsert_statement(
            self.session,
            payloads,
            Station.__table__,
            [
                "postal_code",
                "address",
                "address_normalized",
                "locality",
                "locality_normalized",
                "municipality",
                "municipality_normalized",
                "province",
                "province_normalized",
                "brand",
                "brand_normalized",
                "schedule",
                "margin",
                "sale_type",
                "remision",
                "locality_code",
                "province_code",
                "autonomous_region_code",
                "latitude",
                "longitude",
                "is_active",
                "updated_at",
            ],
        )
        await self.session.execute(statement)

    async def get_by_ideess(self, ideess: str) -> Station | None:
        result = await self.session.execute(select(Station).where(Station.ideess == ideess))
        return result.scalar_one_or_none()

    async def get_postal_code_centroid(self, postal_code: str) -> tuple[Decimal, Decimal] | None:
        stmt = select(
            func.avg(Station.latitude),
            func.avg(Station.longitude),
        ).where(
            Station.is_active.is_(True),
            Station.latitude.is_not(None),
            Station.longitude.is_not(None),
            or_(
                Station.postal_code == postal_code,
                Station.postal_code_resolved == postal_code,
            ),
        )
        result = await self.session.execute(stmt)
        latitude, longitude = result.one()
        if latitude is None or longitude is None:
            return None
        return Decimal(str(latitude)), Decimal(str(longitude))

    async def list_pending_postal_code_resolution(self, *, limit: int) -> list[Station]:
        if limit <= 0:
            return []
        stmt = (
            select(Station)
            .where(
                Station.is_active.is_(True),
                Station.latitude.is_not(None),
                Station.longitude.is_not(None),
                Station.postal_code_checked_at.is_(None),
            )
            .order_by(Station.ideess.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_postal_code_resolutions(self, payloads: list[dict]) -> None:
        if not payloads:
            return
        statement = (
            update(Station.__table__)
            .where(Station.__table__.c.ideess == bindparam("station_ideess"))
            .values(
                postal_code_resolved=bindparam("postal_code_resolved"),
                postal_code_checked_at=bindparam("postal_code_checked_at"),
            )
        )
        await self.session.execute(
            statement,
            [
                {
                    "station_ideess": payload["ideess"],
                    "postal_code_resolved": payload["postal_code_resolved"],
                    "postal_code_checked_at": payload["postal_code_checked_at"],
                }
                for payload in payloads
            ],
        )

    async def reset_postal_code_resolution_status(self, *, clear_resolved: bool = False) -> int:
        values: dict[str, object] = {"postal_code_checked_at": None}
        if clear_resolved:
            values["postal_code_resolved"] = None

        statement = (
            update(Station.__table__)
            .where(
                Station.is_active.is_(True),
                Station.latitude.is_not(None),
                Station.longitude.is_not(None),
            )
            .values(**values)
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)

    async def search(
        self,
        *,
        postal_code: str | None = None,
        radius_center_latitude: float | None = None,
        radius_center_longitude: float | None = None,
        radius_km: int | None = None,
        province: str | None = None,
        municipality: str | None = None,
        locality: str | None = None,
        brand: str | None = None,
        address_text: str | None = None,
        fuel_id: int | None = None,
        page: int = 1,
        page_size: int = 5,
    ) -> tuple[list[Station], int]:
        filters = [Station.is_active.is_(True)]
        distance_order_expr = None
        matched_price_expr = None
        postal_code_filter = None
        radius_filter = None
        if postal_code:
            postal_code_filter = or_(
                Station.postal_code_resolved == postal_code,
                Station.postal_code == postal_code,
            )
        if (
            radius_km is not None
            and radius_km > 0
            and radius_center_latitude is not None
            and radius_center_longitude is not None
        ):
            latitude_scale = 111.32
            longitude_scale = 111.32 * max(cos(radians(radius_center_latitude)), 0.01)
            latitude_diff_km = (cast(Station.latitude, Float) - radius_center_latitude) * latitude_scale
            longitude_diff_km = (cast(Station.longitude, Float) - radius_center_longitude) * longitude_scale
            distance_order_expr = (latitude_diff_km * latitude_diff_km) + (longitude_diff_km * longitude_diff_km)
            radius_filter = and_(
                Station.latitude.is_not(None),
                Station.longitude.is_not(None),
                distance_order_expr <= float(radius_km * radius_km),
            )
        if postal_code_filter is not None and radius_filter is not None:
            filters.append(or_(postal_code_filter, radius_filter))
        elif postal_code_filter is not None:
            filters.append(postal_code_filter)
        elif radius_filter is not None:
            filters.append(radius_filter)
        if province:
            filters.append(Station.province_normalized.like(f"{normalize_text(province)}%"))
        if municipality:
            filters.append(Station.municipality_normalized.like(f"{normalize_text(municipality)}%"))
        if locality:
            filters.append(Station.locality_normalized.like(f"{normalize_text(locality)}%"))
        if brand:
            filters.append(Station.brand_normalized.like(f"{normalize_text(brand)}%"))
        if address_text:
            normalized = normalize_text(address_text)
            filters.append(
                or_(
                    Station.address_normalized.like(f"%{normalized}%"),
                    Station.brand_normalized.like(f"%{normalized}%"),
                    Station.municipality_normalized.like(f"%{normalized}%"),
                    Station.locality_normalized.like(f"%{normalized}%"),
                )
            )

        base_stmt: Select = select(Station).where(and_(*filters))
        if fuel_id is not None:
            matched_price_expr = StationPriceCurrent.current_price.label("matched_price")
            base_stmt = base_stmt.add_columns(matched_price_expr)
            base_stmt = base_stmt.join(
                StationPriceCurrent,
                and_(
                    StationPriceCurrent.station_id == Station.ideess,
                    StationPriceCurrent.fuel_id == fuel_id,
                    StationPriceCurrent.is_available.is_(True),
                ),
            )

        count_subquery = base_stmt.with_only_columns(Station.ideess).distinct().subquery()
        count_stmt = select(func.count()).select_from(count_subquery)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        order_by = []
        if matched_price_expr is not None:
            order_by.append(matched_price_expr.asc())
        order_by.append(distance_order_expr.asc() if distance_order_expr is not None else Station.province.asc())
        order_by.extend(
            [
                Station.municipality.asc(),
                Station.brand.asc(),
                Station.address.asc(),
            ]
        )
        stmt = (
            base_stmt.order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        if matched_price_expr is None:
            return list(result.scalars().unique().all()), total

        stations: list[Station] = []
        for station, matched_price in result.all():
            station.search_price = matched_price
            stations.append(station)
        return stations, total

    async def list_station_fuels(self, ideess: str) -> list[tuple[Fuel, StationPriceCurrent]]:
        stmt = (
            select(Fuel, StationPriceCurrent)
            .join(StationPriceCurrent, StationPriceCurrent.fuel_id == Fuel.id)
            .where(
                StationPriceCurrent.station_id == ideess,
                StationPriceCurrent.is_available.is_(True),
                Fuel.is_active.is_(True),
            )
            .order_by(Fuel.display_order)
        )
        rows = await self.session.execute(stmt)
        return list(rows.all())
