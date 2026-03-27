from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.bot.keyboards import build_watchlist_actions
from app.bot.router import _render_watchlists_text
from app.models.enums import WatchlistStatus
from app.models.station import Station
from app.models.station_price import StationPriceCurrent
from app.models.user import User
from app.repositories.station_prices import StationPricesRepository
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
            station_id="300",
            fuel_id=1,
            status=WatchlistStatus.ACTIVE,
            station=SimpleNamespace(brand="SERMUCO"),
            fuel=SimpleNamespace(name="Gasoleo A"),
        ),
        SimpleNamespace(
            id=1,
            station_id="301",
            fuel_id=1,
            status=WatchlistStatus.PAUSED,
            station=SimpleNamespace(brand="CAMPSA EXPRESS"),
            fuel=SimpleNamespace(name="Gasoleo A"),
        ),
    ]
    price_map = {
        ("300", 1): SimpleNamespace(current_price=Decimal("1.696")),
        ("301", 1): SimpleNamespace(current_price=Decimal("1.589")),
    }

    markup = build_watchlist_actions(watchlists, page=1, total=2, page_size=10, price_map=price_map)

    assert [[button.text for button in row] for row in markup.inline_keyboard] == [
        ["▶️ SERMUCO | Gasoleo A | 1.696€/L"],
        ["Pausar", "Eliminar"],
        ["⏸ CAMPSA EXPRESS | Gasoleo A | 1.589€/L"],
        ["Reanudar", "Eliminar"],
    ]


def test_render_watchlists_text_hides_internal_id_and_shows_price() -> None:
    watchlists = [
        SimpleNamespace(
            id=7,
            station_id="300",
            fuel_id=1,
            status=WatchlistStatus.ACTIVE,
            station=SimpleNamespace(
                brand="SERMUCO",
                address="POLIGONO LOS PRADOS, 6",
                municipality="Cieza",
            ),
            fuel=SimpleNamespace(name="Gasoleo A"),
        )
    ]
    price_map = {("300", 1): SimpleNamespace(current_price=Decimal("1.696"))}

    text = _render_watchlists_text(watchlists, page=1, total=1, page_size=10, price_map=price_map)

    assert "#7" not in text
    assert "Gasoleo A | 1.696€/L | Activa" in text


async def test_load_current_price_map_for_pairs_returns_only_requested_prices(session_factory) -> None:
    async with session_factory() as session:
        tz = ZoneInfo("Europe/Madrid")
        session.add_all(
            [
                Station(
                    ideess="300",
                    postal_code="30001",
                    address="Calle Uno 1",
                    address_normalized="calle uno 1",
                    locality="Murcia",
                    locality_normalized="murcia",
                    municipality="Murcia",
                    municipality_normalized="murcia",
                    province="Murcia",
                    province_normalized="murcia",
                    brand="SERMUCO",
                    brand_normalized="sermuco",
                    is_active=True,
                ),
                Station(
                    ideess="301",
                    postal_code="30002",
                    address="Calle Dos 2",
                    address_normalized="calle dos 2",
                    locality="Murcia",
                    locality_normalized="murcia",
                    municipality="Murcia",
                    municipality_normalized="murcia",
                    province="Murcia",
                    province_normalized="murcia",
                    brand="CAMPSA EXPRESS",
                    brand_normalized="campsa express",
                    is_active=True,
                ),
            ]
        )
        session.add_all(
            [
                StationPriceCurrent(
                    station_id="300",
                    fuel_id=1,
                    current_price=Decimal("1.696"),
                    dataset_timestamp=datetime(2026, 3, 27, 11, 30, tzinfo=tz),
                    last_seen_at=datetime(2026, 3, 27, 11, 30, tzinfo=tz),
                    last_changed_at=datetime(2026, 3, 27, 11, 30, tzinfo=tz),
                    is_available=True,
                ),
                StationPriceCurrent(
                    station_id="301",
                    fuel_id=1,
                    current_price=Decimal("1.589"),
                    dataset_timestamp=datetime(2026, 3, 27, 11, 30, tzinfo=tz),
                    last_seen_at=datetime(2026, 3, 27, 11, 30, tzinfo=tz),
                    last_changed_at=datetime(2026, 3, 27, 11, 30, tzinfo=tz),
                    is_available=False,
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        price_map = await StationPricesRepository(session).load_current_price_map_for_pairs([("300", 1), ("301", 1)])

    assert list(price_map) == [("300", 1)]
    assert price_map[("300", 1)].current_price == Decimal("1.696")
