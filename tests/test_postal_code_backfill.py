from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.integrations.postal_code_api import PostalCodeResolution
from app.models.station import Station
from app.services.postal_code_backfill_service import PostalCodeBackfillService


class FakePostalCodeClient:
    def __init__(self, resolutions: dict[str, str | None]) -> None:
        self.enabled = True
        self.batch_size = 10
        self.resolutions = resolutions

    async def resolve_postal_codes(self, stations):
        return {
            station_id: PostalCodeResolution(postal_code=self.resolutions.get(station_id), checked=True)
            for station_id, _, _ in stations
        }


async def test_postal_code_backfill_refreshes_all_pending_stations(session_factory) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                Station(
                    ideess="100",
                    postal_code="28001",
                    postal_code_resolved="28002",
                    postal_code_checked_at=None,
                    address="A",
                    address_normalized="a",
                    locality="Madrid",
                    locality_normalized="madrid",
                    municipality="Madrid",
                    municipality_normalized="madrid",
                    province="Madrid",
                    province_normalized="madrid",
                    brand="Marca",
                    brand_normalized="marca",
                    latitude=Decimal("40.1"),
                    longitude=Decimal("-3.1"),
                    is_active=True,
                ),
                Station(
                    ideess="200",
                    postal_code="08001",
                    postal_code_resolved="08002",
                    postal_code_checked_at=None,
                    address="B",
                    address_normalized="b",
                    locality="Barcelona",
                    locality_normalized="barcelona",
                    municipality="Barcelona",
                    municipality_normalized="barcelona",
                    province="Barcelona",
                    province_normalized="barcelona",
                    brand="Marca",
                    brand_normalized="marca",
                    latitude=Decimal("41.1"),
                    longitude=Decimal("2.1"),
                    is_active=True,
                ),
            ]
        )
        await session.commit()

        service = PostalCodeBackfillService(
            session=session,
            postal_code_client=FakePostalCodeClient({"100": "28003", "200": None}),
        )

        stats = await service.run(delay_seconds=0, max_batches=1)

        assert stats == {
            "batches_processed": 1,
            "stations_seen": 2,
            "stations_checked": 2,
            "stations_corrected": 1,
        }

    async with session_factory() as session:
        station_100 = await session.get(Station, "100")
        station_200 = await session.get(Station, "200")

        assert station_100 is not None
        assert station_100.postal_code_resolved == "28003"
        assert station_100.postal_code_checked_at is not None

        assert station_200 is not None
        assert station_200.postal_code_resolved is None
        assert station_200.postal_code_checked_at is not None


async def test_postal_code_backfill_reset_reopens_queue_without_clearing_resolved(session_factory) -> None:
    async with session_factory() as session:
        station = Station(
            ideess="300",
            postal_code="30001",
            postal_code_resolved="30002",
            postal_code_checked_at=datetime(2026, 3, 27, 9, 0, tzinfo=ZoneInfo("Europe/Madrid")),
            address="C",
            address_normalized="c",
            locality="Murcia",
            locality_normalized="murcia",
            municipality="Murcia",
            municipality_normalized="murcia",
            province="Murcia",
            province_normalized="murcia",
            brand="Marca",
            brand_normalized="marca",
            latitude=Decimal("37.9"),
            longitude=Decimal("-1.1"),
            is_active=True,
        )
        session.add(station)
        await session.commit()

        service = PostalCodeBackfillService(
            session=session,
            postal_code_client=FakePostalCodeClient({}),
        )

        reset_count = await service.reset_all(clear_resolved=False)

        assert reset_count == 1

    async with session_factory() as session:
        station = await session.get(Station, "300")
        assert station is not None
        assert station.postal_code_resolved == "30002"
        assert station.postal_code_checked_at is None
