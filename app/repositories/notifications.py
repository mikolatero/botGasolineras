from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.enums import NotificationStatus
from app.models.notification import NotificationSent
from app.models.watchlist import UserWatchlist
from app.repositories.base import Repository


class NotificationsRepository(Repository):
    async def bulk_create_pending(self, payloads: list[dict]) -> None:
        if payloads:
            await self.session.execute(NotificationSent.__table__.insert(), payloads)

    async def fetch_pending(self, limit: int = 100) -> list[NotificationSent]:
        stmt = (
            select(NotificationSent)
            .options(
                joinedload(NotificationSent.watchlist).joinedload(UserWatchlist.user),
                joinedload(NotificationSent.station),
                joinedload(NotificationSent.fuel),
            )
            .where(NotificationSent.status == NotificationStatus.PENDING)
            .order_by(NotificationSent.id.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def mark_sent(self, notification: NotificationSent, telegram_message_id: int | None, sent_at: datetime) -> None:
        notification.status = NotificationStatus.SENT
        notification.telegram_message_id = telegram_message_id
        notification.sent_at = sent_at
        notification.error_message = None
        await self.session.flush()

    async def mark_failed(self, notification: NotificationSent, error_message: str) -> None:
        notification.status = NotificationStatus.FAILED
        notification.error_message = error_message[:1000]
        await self.session.flush()
