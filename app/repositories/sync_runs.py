from __future__ import annotations

from datetime import datetime

from app.models.enums import SyncRunStatus
from app.models.sync_run import SyncRun
from app.repositories.base import Repository


class SyncRunsRepository(Repository):
    async def create_started(self, started_at: datetime) -> SyncRun:
        item = SyncRun(status=SyncRunStatus.RUNNING, started_at=started_at)
        self.session.add(item)
        await self.session.flush()
        return item

    async def mark_success(
        self,
        sync_run: SyncRun,
        *,
        finished_at: datetime,
        dataset_timestamp: datetime,
        stations_received: int,
        price_rows_received: int,
        price_rows_changed: int,
        price_drops_detected: int,
    ) -> None:
        sync_run.status = SyncRunStatus.SUCCESS
        sync_run.finished_at = finished_at
        sync_run.dataset_timestamp = dataset_timestamp
        sync_run.stations_received = stations_received
        sync_run.price_rows_received = price_rows_received
        sync_run.price_rows_changed = price_rows_changed
        sync_run.price_drops_detected = price_drops_detected
        sync_run.error_message = None
        await self.session.flush()

    async def mark_failed(self, sync_run: SyncRun, *, finished_at: datetime, error_message: str) -> None:
        sync_run.status = SyncRunStatus.FAILED
        sync_run.finished_at = finished_at
        sync_run.error_message = error_message[:4000]
        await self.session.flush()
