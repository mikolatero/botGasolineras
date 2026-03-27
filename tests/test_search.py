from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.bot.keyboards import build_search_results
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


def test_build_search_results_uses_one_button_per_row_and_matching_indexes() -> None:
    stations = [
        SimpleNamespace(ideess="300", brand="MOEVE", municipality="Murcia", address="CARRETERA MU-611 KM. 3"),
        SimpleNamespace(ideess="301", brand="CAMPSA EXPRESS", municipality="Murcia", address="PG INDTL. OESTE S. GINES PARC., 29"),
    ]

    markup = build_search_results(stations, page=2, total=12, page_size=5)

    assert [[button.text for button in row] for row in markup.inline_keyboard] == [
        ["6. MOEVE | Murcia | CARRETERA MU-611 KM. 3"],
        ["7. CAMPSA EXPRESS | Murcia | PG INDTL. OESTE S. GINES PAR"],
        ["⬅️ Anterior"],
        ["Siguiente ➡️"],
        ["Editar filtros"],
    ]
