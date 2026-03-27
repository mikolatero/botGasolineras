from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import and_, select, tuple_, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.station_price import StationPriceCurrent, StationPriceHistory
from app.repositories.base import Repository


class StationPricesRepository(Repository):
    async def load_current_price_map(self) -> dict[tuple[str, int], StationPriceCurrent]:
        result = await self.session.execute(select(StationPriceCurrent))
        rows = result.scalars().all()
        return {(row.station_id, row.fuel_id): row for row in rows}

    async def load_current_price_map_for_pairs(
        self, pairs: Iterable[tuple[str, int]]
    ) -> dict[tuple[str, int], StationPriceCurrent]:
        keys = list(pairs)
        if not keys:
            return {}

        result = await self.session.execute(
            select(StationPriceCurrent).where(
                tuple_(StationPriceCurrent.station_id, StationPriceCurrent.fuel_id).in_(keys),
                StationPriceCurrent.is_available.is_(True),
            )
        )
        rows = result.scalars().all()
        return {(row.station_id, row.fuel_id): row for row in rows}

    async def upsert_current_many(self, payloads: list[dict]) -> None:
        if not payloads:
            return

        dialect = self.session.bind.dialect.name
        if dialect == "mysql":
            stmt = mysql_insert(StationPriceCurrent.__table__).values(payloads)
            statement = stmt.on_duplicate_key_update(
                current_price=stmt.inserted.current_price,
                dataset_timestamp=stmt.inserted.dataset_timestamp,
                last_seen_at=stmt.inserted.last_seen_at,
                last_changed_at=stmt.inserted.last_changed_at,
                is_available=stmt.inserted.is_available,
            )
        elif dialect == "sqlite":
            stmt = sqlite_insert(StationPriceCurrent.__table__).values(payloads)
            statement = stmt.on_conflict_do_update(
                index_elements=["station_id", "fuel_id"],
                set_={
                    "current_price": stmt.excluded.current_price,
                    "dataset_timestamp": stmt.excluded.dataset_timestamp,
                    "last_seen_at": stmt.excluded.last_seen_at,
                    "last_changed_at": stmt.excluded.last_changed_at,
                    "is_available": stmt.excluded.is_available,
                },
            )
        else:
            raise RuntimeError(f"Unsupported dialect for upsert: {dialect}")
        await self.session.execute(statement)

    async def mark_missing_unavailable(self, available_keys: Iterable[tuple[str, int]], dataset_timestamp: datetime) -> None:
        keys = list(available_keys)
        if not keys:
            return
        statement = (
            update(StationPriceCurrent)
            .where(~tuple_(StationPriceCurrent.station_id, StationPriceCurrent.fuel_id).in_(keys))
            .values(is_available=False, last_seen_at=dataset_timestamp)
        )
        await self.session.execute(statement)

    async def insert_history_many(self, payloads: list[dict]) -> None:
        if payloads:
            await self.session.execute(StationPriceHistory.__table__.insert(), payloads)
