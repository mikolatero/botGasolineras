from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.database import SessionLocal
from app.config.settings import get_settings
from app.integrations.fuel_api import MineturApiClient
from app.repositories.notifications import NotificationsRepository
from app.repositories.watchlists import WatchlistsRepository
from app.services.notification_service import NotificationService
from app.services.sync_service import SyncService
from app.utils.timezone import madrid_tz

logger = logging.getLogger(__name__)


class WorkerRunner:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=madrid_tz())
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self.scheduler.add_job(
            self.run_cycle,
            trigger=IntervalTrigger(minutes=self.settings.sync_interval_minutes, timezone=madrid_tz()),
            max_instances=1,
            coalesce=True,
            id="station-sync-job",
            replace_existing=True,
        )
        self.scheduler.start()
        if self.settings.run_sync_on_startup:
            asyncio.create_task(self.run_cycle())

    async def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        await self.bot.session.close()

    async def run_cycle(self) -> None:
        if self._lock.locked():
            logger.info("Sync already running, skipping overlapping execution")
            return

        async with self._lock:
            async with SessionLocal() as session:
                sync_service = SyncService(session=session, client=MineturApiClient(self.settings))
                notification_service = NotificationService(
                    bot=self.bot,
                    notifications_repository=NotificationsRepository(session),
                    watchlists_repository=WatchlistsRepository(session),
                )
                await sync_service.run_sync()
                delivered = await notification_service.dispatch_pending(limit=200)
                await session.commit()
                logger.info("Worker cycle completed, delivered=%s", delivered)

