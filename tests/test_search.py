from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from app.bot import router
from app.bot.keyboards import build_search_results
from app.bot.router import _render_filter_summary, _render_search_results_text
from app.models.station import Station
from app.models.station_price import StationPriceCurrent
from app.repositories.stations import StationsRepository
from app.services.search_service import SearchFilters, SearchService


async def test_search_filters_against_local_database(session_factory) -> None:
    async with session_factory() as session:
        tz = ZoneInfo("Europe/Madrid")
        station_one = Station(
            ideess="100",
            postal_code="30001",
            address="Av. Libertad 1",
            address_normalized="av. libertad 1",
            locality="Murcia",
            locality_normalized="murcia",
            municipality="Murcia",
            municipality_normalized="murcia",
            province="Murcia",
            province_normalized="murcia",
            brand="Repsol",
            brand_normalized="repsol",
            sale_type="P",
            is_active=True,
        )
        station_two = Station(
            ideess="200",
            postal_code="46001",
            address="Gran Via 10",
            address_normalized="gran via 10",
            locality="Valencia",
            locality_normalized="valencia",
            municipality="Valencia",
            municipality_normalized="valencia",
            province="Valencia",
            province_normalized="valencia",
            brand="Cepsa",
            brand_normalized="cepsa",
            sale_type="P",
            is_active=True,
        )
        session.add_all([station_one, station_two])
        session.add_all(
            [
                StationPriceCurrent(
                    station_id="100",
                    fuel_id=1,
                    current_price=Decimal("1.400"),
                    dataset_timestamp=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_seen_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_changed_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    is_available=True,
                ),
                StationPriceCurrent(
                    station_id="200",
                    fuel_id=4,
                    current_price=Decimal("1.550"),
                    dataset_timestamp=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_seen_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_changed_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    is_available=True,
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        service = SearchService(StationsRepository(session))
        stations, total = await service.search(
            SearchFilters(province="Murcia", brand="Rep", fuel_id=1),
            page=1,
            page_size=10,
        )
        assert total == 1
        assert len(stations) == 1
        assert stations[0].ideess == "100"

    async with session_factory() as session:
        service = SearchService(StationsRepository(session))
        stations, total = await service.search(
            SearchFilters(address_text="gran via"),
            page=1,
            page_size=10,
        )
        assert total == 1
        assert stations[0].ideess == "200"


async def test_search_with_fuel_orders_results_by_price_ascending(session_factory) -> None:
    async with session_factory() as session:
        tz = ZoneInfo("Europe/Madrid")
        station_one = Station(
            ideess="300",
            postal_code="30001",
            address="Av. Cara 1",
            address_normalized="av. cara 1",
            locality="Murcia",
            locality_normalized="murcia",
            municipality="Murcia",
            municipality_normalized="murcia",
            province="Murcia",
            province_normalized="murcia",
            brand="Marca Cara",
            brand_normalized="marca cara",
            sale_type="P",
            is_active=True,
        )
        station_two = Station(
            ideess="301",
            postal_code="30001",
            address="Av. Barata 2",
            address_normalized="av. barata 2",
            locality="Murcia",
            locality_normalized="murcia",
            municipality="Murcia",
            municipality_normalized="murcia",
            province="Murcia",
            province_normalized="murcia",
            brand="Marca Barata",
            brand_normalized="marca barata",
            sale_type="P",
            is_active=True,
        )
        session.add_all([station_one, station_two])
        session.add_all(
            [
                StationPriceCurrent(
                    station_id="300",
                    fuel_id=1,
                    current_price=Decimal("1.599"),
                    dataset_timestamp=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_seen_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_changed_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    is_available=True,
                ),
                StationPriceCurrent(
                    station_id="301",
                    fuel_id=1,
                    current_price=Decimal("1.429"),
                    dataset_timestamp=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_seen_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    last_changed_at=datetime(2026, 3, 25, 12, 30, tzinfo=tz),
                    is_available=True,
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        service = SearchService(StationsRepository(session))
        stations, total = await service.search(
            SearchFilters(postal_code="30001", fuel_id=1),
            page=1,
            page_size=10,
        )

        assert total == 2
        assert [station.ideess for station in stations] == ["301", "300"]
        assert [station.search_price for station in stations] == [Decimal("1.429"), Decimal("1.599")]


async def test_search_only_returns_public_sale_type_stations(session_factory) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                Station(
                    ideess="700",
                    postal_code="30001",
                    address="Publica 1",
                    address_normalized="publica 1",
                    locality="Murcia",
                    locality_normalized="murcia",
                    municipality="Murcia",
                    municipality_normalized="murcia",
                    province="Murcia",
                    province_normalized="murcia",
                    brand="Marca Publica",
                    brand_normalized="marca publica",
                    sale_type="P",
                    is_active=True,
                ),
                Station(
                    ideess="701",
                    postal_code="30001",
                    address="Privada 2",
                    address_normalized="privada 2",
                    locality="Murcia",
                    locality_normalized="murcia",
                    municipality="Murcia",
                    municipality_normalized="murcia",
                    province="Murcia",
                    province_normalized="murcia",
                    brand="Marca Privada",
                    brand_normalized="marca privada",
                    sale_type="R",
                    is_active=True,
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        service = SearchService(StationsRepository(session))
        stations, total = await service.search(
            SearchFilters(postal_code="30001"),
            page=1,
            page_size=10,
        )

        assert total == 1
        assert [station.ideess for station in stations] == ["700"]


async def test_get_by_ideess_public_only_excludes_private_stations(session_factory) -> None:
    async with session_factory() as session:
        session.add(
            Station(
                ideess="702",
                postal_code="30001",
                address="Privada 3",
                address_normalized="privada 3",
                locality="Murcia",
                locality_normalized="murcia",
                municipality="Murcia",
                municipality_normalized="murcia",
                province="Murcia",
                province_normalized="murcia",
                brand="Marca Restringida",
                brand_normalized="marca restringida",
                sale_type="R",
                is_active=True,
            )
        )
        await session.commit()

    async with session_factory() as session:
        repository = StationsRepository(session)

        assert await repository.get_by_ideess("702") is not None
        assert await repository.get_by_ideess("702", public_only=True) is None


def test_build_search_results_uses_one_button_per_row_and_matching_indexes() -> None:
    stations = [
        SimpleNamespace(
            ideess="300",
            brand="MOEVE",
            municipality="Murcia",
            address="CARRETERA MU-611 KM. 3",
            search_price=Decimal("1.409"),
        ),
        SimpleNamespace(
            ideess="301",
            brand="CAMPSA EXPRESS",
            municipality="Murcia",
            address="PG INDTL. OESTE S. GINES PARC., 29",
            search_price=Decimal("1.379"),
        ),
    ]

    markup = build_search_results(stations, page=2, total=12, page_size=5)

    assert [[button.text for button in row] for row in markup.inline_keyboard] == [
        ["6. MOEVE | Murcia | 1.409€/L | CARRETERA MU-611 K"],
        ["7. CAMPSA EXPRESS | Murcia | 1.379€/L | PG INDTL. OESTE S."],
        ["⬅️ Anterior"],
        ["Siguiente ➡️"],
        ["Editar filtros"],
    ]


def test_render_search_results_text_shows_price_when_available() -> None:
    stations = [
        SimpleNamespace(
            ideess="300",
            brand="MOEVE",
            municipality="Murcia",
            address="CARRETERA MU-611 KM. 3",
            postal_code_display="30001",
            search_price=Decimal("1.409"),
        ),
        SimpleNamespace(
            ideess="301",
            brand="CAMPSA EXPRESS",
            municipality="Murcia",
            address="PG INDTL. OESTE S. GINES PARC., 29",
            postal_code_display="30002",
            search_price=Decimal("1.379"),
        ),
    ]

    text = _render_search_results_text(stations, page=1, total=2, page_size=5)

    assert "1. <b>MOEVE</b> - CARRETERA MU-611 KM. 3, Murcia (30001) | 1.409€/L" in text
    assert "2. <b>CAMPSA EXPRESS</b> - PG INDTL. OESTE S. GINES PARC., 29, Murcia (30002) | 1.379€/L" in text


def test_render_filter_summary_shows_fuel_name_instead_of_id() -> None:
    text = _render_filter_summary(
        {
            "postal_code": "30169",
            "radius_km": 5,
            "province": None,
            "municipality": None,
            "locality": None,
            "brand": None,
            "address_text": None,
            "fuel_id": 1,
        }
    )

    assert "• <b>Combustible:</b> Gasoleo A" in text
    assert "• <b>Combustible:</b> 1" not in text


@pytest.mark.asyncio
async def test_search_clear_handler_skips_menu_refresh_when_no_filters(monkeypatch) -> None:
    show_search_menu = AsyncMock()
    monkeypatch.setattr(router, "_show_search_menu", show_search_menu)

    callback = SimpleNamespace(answer=AsyncMock())
    state = SimpleNamespace(get_data=AsyncMock(return_value={}), clear=AsyncMock())

    await router.search_clear_handler(callback, state)

    state.clear.assert_awaited_once()
    show_search_menu.assert_not_awaited()
    callback.answer.assert_awaited_once_with("No habia filtros activos.")
