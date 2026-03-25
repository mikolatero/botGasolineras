from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.notification import NotificationSent
from app.models.user import User
from app.models.watchlist import UserWatchlist
from app.repositories.watchlists import WatchlistsRepository
from app.services.sync_service import SyncService


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

