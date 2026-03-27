from __future__ import annotations

from types import SimpleNamespace

from app.bot.keyboards import build_watchlist_actions
from app.models.enums import WatchlistStatus
from app.models.station import Station
from app.models.user import User
from app.repositories.watchlists import WatchlistsRepository
from app.utils.timezone import now_madrid


async def test_watchlist_unique_and_reactivation(session_factory) -> None:
    created_user_id = None
    async with session_factory() as session:
        session.add(
            Station(
                ideess="300",
                postal_code="28001",
                address="Calle Alcala 1",
                address_normalized="calle alcala 1",
                locality="Madrid",
                locality_normalized="madrid",
                municipality="Madrid",
                municipality_normalized="madrid",
                province="Madrid",
                province_normalized="madrid",
                brand="BP",
                brand_normalized="bp",
                is_active=True,
            )
        )
        user = User(telegram_user_id=222, username="watcher", first_name="Watch", last_name="List")
        session.add(user)
        await session.flush()
        created_user_id = user.id

        repository = WatchlistsRepository(session)
        watchlist, created = await repository.create_or_reactivate(user.id, "300", 1)
        assert created is True
        await repository.pause(watchlist, now_madrid())
        await session.commit()

    async with session_factory() as session:
        repository = WatchlistsRepository(session)
        watchlist, created = await repository.create_or_reactivate(created_user_id, "300", 1)
        assert created is False
        assert watchlist.status.value == "active"
        await session.commit()


def test_build_watchlist_actions_keeps_each_watchlist_grouped() -> None:
    watchlists = [
        SimpleNamespace(
            id=7,
            status=WatchlistStatus.ACTIVE,
            station=SimpleNamespace(brand="SERMUCO"),
            fuel=SimpleNamespace(name="Gasoleo A"),
        ),
        SimpleNamespace(
            id=1,
            status=WatchlistStatus.PAUSED,
            station=SimpleNamespace(brand="CAMPSA EXPRESS"),
            fuel=SimpleNamespace(name="Gasoleo A"),
        ),
    ]

    markup = build_watchlist_actions(watchlists, page=1, total=2, page_size=10)

    assert [[button.text for button in row] for row in markup.inline_keyboard] == [
        ["▶️ SERMUCO | Gasoleo A"],
        ["Pausar", "Eliminar"],
        ["⏸ CAMPSA EXPRESS | Gasoleo A"],
        ["Reanudar", "Eliminar"],
    ]
