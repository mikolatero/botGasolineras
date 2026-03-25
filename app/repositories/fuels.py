from __future__ import annotations

from sqlalchemy import select

from app.config.constants import FUEL_DEFINITIONS
from app.models.fuel import Fuel
from app.repositories.base import Repository


class FuelsRepository(Repository):
    async def seed_defaults(self) -> None:
        result = await self.session.execute(select(Fuel.id))
        if result.first() is not None:
            return

        for item in FUEL_DEFINITIONS:
            self.session.add(
                Fuel(
                    id=int(item["id"]),
                    code=str(item["code"]),
                    name=str(item["name"]),
                    dataset_key=str(item["dataset_key"]),
                    display_order=int(item["order"]),
                    is_active=True,
                )
            )
        await self.session.flush()

    async def list_active(self) -> list[Fuel]:
        result = await self.session.execute(select(Fuel).where(Fuel.is_active.is_(True)).order_by(Fuel.display_order))
        return list(result.scalars().all())

    async def get_by_id(self, fuel_id: int) -> Fuel | None:
        result = await self.session.execute(select(Fuel).where(Fuel.id == fuel_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Fuel | None:
        result = await self.session.execute(select(Fuel).where(Fuel.code == code))
        return result.scalar_one_or_none()

