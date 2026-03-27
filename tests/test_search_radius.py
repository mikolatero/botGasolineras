from __future__ import annotations

from decimal import Decimal

from app.models.postal_code_location import PostalCodeLocation
from app.models.station import Station
from app.repositories.postal_code_locations import PostalCodeLocationsRepository
from app.repositories.stations import StationsRepository
from app.services.search_service import SearchFilters, SearchService


class FakePostalCodeGeoClient:
    def __init__(self, coordinates_by_postal_code: dict[str, tuple[Decimal, Decimal] | None]) -> None:
        self.coordinates_by_postal_code = coordinates_by_postal_code

    async def geocode_postal_code(self, postal_code: str):
        return self.coordinates_by_postal_code.get(postal_code)


async def test_search_radius_finds_nearby_stations_from_adjacent_postal_codes(session_factory) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                Station(
                    ideess="100",
                    postal_code="28001",
                    address="Centro 1",
                    address_normalized="centro 1",
                    locality="Madrid",
                    locality_normalized="madrid",
                    municipality="Madrid",
                    municipality_normalized="madrid",
                    province="Madrid",
                    province_normalized="madrid",
                    brand="Marca A",
                    brand_normalized="marca a",
                    latitude=Decimal("40.0010000"),
                    longitude=Decimal("-3.7000000"),
                    is_active=True,
                ),
                Station(
                    ideess="200",
                    postal_code="28002",
                    address="Cercana 2",
                    address_normalized="cercana 2",
                    locality="Madrid",
                    locality_normalized="madrid",
                    municipality="Madrid",
                    municipality_normalized="madrid",
                    province="Madrid",
                    province_normalized="madrid",
                    brand="Marca B",
                    brand_normalized="marca b",
                    latitude=Decimal("40.0250000"),
                    longitude=Decimal("-3.7000000"),
                    is_active=True,
                ),
                Station(
                    ideess="300",
                    postal_code="28003",
                    address="Lejana 3",
                    address_normalized="lejana 3",
                    locality="Madrid",
                    locality_normalized="madrid",
                    municipality="Madrid",
                    municipality_normalized="madrid",
                    province="Madrid",
                    province_normalized="madrid",
                    brand="Marca C",
                    brand_normalized="marca c",
                    latitude=Decimal("40.0900000"),
                    longitude=Decimal("-3.7000000"),
                    is_active=True,
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        service = SearchService(
            StationsRepository(session),
            PostalCodeLocationsRepository(session),
            FakePostalCodeGeoClient({"28001": (Decimal("40.0000000"), Decimal("-3.7000000"))}),
        )
        stations, total = await service.search(
            SearchFilters(postal_code="28001", radius_km=5),
            page=1,
            page_size=10,
        )
        await session.commit()

        assert total == 2
        assert [station.ideess for station in stations] == ["100", "200"]

        cached = await session.get(PostalCodeLocation, "28001")
        assert cached is not None
        assert cached.latitude == Decimal("40.0000000")
        assert cached.longitude == Decimal("-3.7000000")


async def test_search_radius_falls_back_to_exact_postal_code_when_cp_cannot_be_geocoded(session_factory) -> None:
    async with session_factory() as session:
        session.add(
            Station(
                ideess="400",
                postal_code="30001",
                address="Exacta 1",
                address_normalized="exacta 1",
                locality="Murcia",
                locality_normalized="murcia",
                municipality="Murcia",
                municipality_normalized="murcia",
                province="Murcia",
                province_normalized="murcia",
                brand="Marca D",
                brand_normalized="marca d",
                latitude=Decimal("37.9800000"),
                longitude=Decimal("-1.1200000"),
                is_active=True,
            )
        )
        await session.commit()

    async with session_factory() as session:
        service = SearchService(
            StationsRepository(session),
            PostalCodeLocationsRepository(session),
            FakePostalCodeGeoClient({"30001": None}),
        )
        stations, total = await service.search(
            SearchFilters(postal_code="30001", radius_km=10),
            page=1,
            page_size=10,
        )

        assert total == 1
        assert len(stations) == 1
        assert stations[0].ideess == "400"
