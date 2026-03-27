from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.postal_code_location import PostalCodeLocation
from app.repositories.base import Repository


class PostalCodeLocationsRepository(Repository):
    async def get(self, postal_code: str) -> PostalCodeLocation | None:
        result = await self.session.execute(
            select(PostalCodeLocation).where(PostalCodeLocation.postal_code == postal_code)
        )
        return result.scalar_one_or_none()

    async def upsert(self, *, postal_code: str, latitude: Decimal, longitude: Decimal, updated_at: datetime) -> None:
        payload = {
            "postal_code": postal_code,
            "latitude": latitude,
            "longitude": longitude,
            "updated_at": updated_at,
        }
        dialect = self.session.bind.dialect.name
        if dialect == "mysql":
            stmt = mysql_insert(PostalCodeLocation.__table__).values(payload)
            await self.session.execute(
                stmt.on_duplicate_key_update(
                    latitude=stmt.inserted.latitude,
                    longitude=stmt.inserted.longitude,
                    updated_at=stmt.inserted.updated_at,
                )
            )
            return
        if dialect == "sqlite":
            stmt = sqlite_insert(PostalCodeLocation.__table__).values(payload)
            await self.session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["postal_code"],
                    set_={
                        "latitude": stmt.excluded.latitude,
                        "longitude": stmt.excluded.longitude,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
            )
            return
        raise RuntimeError(f"Unsupported dialect for postal code upsert: {dialect}")
