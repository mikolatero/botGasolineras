from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postal_code_api import CartoCiudadPostalCodeClient, PostalCodeResolution
from app.repositories.stations import StationsRepository
from app.utils.timezone import now_madrid

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PostalCodeBackfillStats:
    batches_processed: int = 0
    stations_seen: int = 0
    stations_checked: int = 0
    stations_corrected: int = 0


class PostalCodeBackfillService:
    def __init__(
        self,
        session: AsyncSession,
        postal_code_client: CartoCiudadPostalCodeClient,
    ) -> None:
        self.session = session
        self.postal_code_client = postal_code_client
        self.stations_repository = StationsRepository(session)

    async def reset_all(self, *, clear_resolved: bool = False) -> int:
        affected = await self.stations_repository.reset_postal_code_resolution_status(clear_resolved=clear_resolved)
        await self.session.commit()
        return affected

    async def run(
        self,
        *,
        delay_seconds: float = 0.0,
        max_batches: int | None = None,
    ) -> dict[str, int]:
        if not self.postal_code_client.enabled or self.postal_code_client.batch_size <= 0:
            logger.info("Postal code backfill skipped because the geocoder is disabled or batch size is 0")
            return asdict(PostalCodeBackfillStats())

        stats = PostalCodeBackfillStats()
        batch_limit = max_batches if max_batches is not None and max_batches > 0 else None
        sanitized_delay = max(delay_seconds, 0.0)

        while batch_limit is None or stats.batches_processed < batch_limit:
            batch_stats = await self._run_single_batch(observed_at=now_madrid())
            if batch_stats.stations_seen == 0:
                break

            stats.batches_processed += 1
            stats.stations_seen += batch_stats.stations_seen
            stats.stations_checked += batch_stats.stations_checked
            stats.stations_corrected += batch_stats.stations_corrected

            logger.info(
                "Postal code backfill batch completed: batch=%s seen=%s checked=%s corrected=%s",
                stats.batches_processed,
                batch_stats.stations_seen,
                batch_stats.stations_checked,
                batch_stats.stations_corrected,
            )

            if sanitized_delay > 0 and (batch_limit is None or stats.batches_processed < batch_limit):
                await asyncio.sleep(sanitized_delay)

        return asdict(stats)

    async def _run_single_batch(self, *, observed_at: datetime) -> PostalCodeBackfillStats:
        stations = await self.stations_repository.list_pending_postal_code_resolution(
            limit=self.postal_code_client.batch_size
        )
        if not stations:
            return PostalCodeBackfillStats()

        resolutions = await self.postal_code_client.resolve_postal_codes(
            [
                (station.ideess, station.latitude, station.longitude)
                for station in stations
                if station.latitude is not None and station.longitude is not None
            ]
        )

        updates: list[dict[str, Any]] = []
        corrected = 0
        for station in stations:
            resolution = resolutions.get(station.ideess)
            if resolution is None or not resolution.checked:
                continue
            if _postal_code_was_corrected(station.postal_code, resolution):
                corrected += 1
            updates.append(
                {
                    "ideess": station.ideess,
                    "postal_code_resolved": resolution.postal_code,
                    "postal_code_checked_at": observed_at,
                }
            )

        await self.stations_repository.update_postal_code_resolutions(updates)
        await self.session.commit()

        return PostalCodeBackfillStats(
            stations_seen=len(stations),
            stations_checked=len(updates),
            stations_corrected=corrected,
        )


def _postal_code_was_corrected(
    official_postal_code: str | None,
    resolution: PostalCodeResolution,
) -> bool:
    return bool(
        official_postal_code
        and resolution.postal_code
        and official_postal_code != resolution.postal_code
    )
