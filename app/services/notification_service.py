from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.repositories.notifications import NotificationsRepository
from app.repositories.watchlists import WatchlistsRepository
from app.utils.formatting import format_notification_message
from app.utils.timezone import now_madrid

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        *,
        bot: Bot,
        notifications_repository: NotificationsRepository,
        watchlists_repository: WatchlistsRepository,
    ) -> None:
        self.bot = bot
        self.notifications_repository = notifications_repository
        self.watchlists_repository = watchlists_repository

    async def dispatch_pending(self, limit: int = 100) -> int:
        notifications = await self.notifications_repository.fetch_pending(limit=limit)
        delivered = 0
        for notification in notifications:
            try:
                message = await self.bot.send_message(
                    chat_id=notification.watchlist.user.telegram_user_id,
                    text=format_notification_message(notification),
                )
                sent_at = now_madrid()
                await self.notifications_repository.mark_sent(notification, message.message_id, sent_at)
                await self.watchlists_repository.mark_notified(notification.watchlist, notification.new_price, sent_at)
                await self.notifications_repository.session.commit()
                delivered += 1
            except TelegramAPIError as exc:
                logger.warning("Unable to send notification %s: %s", notification.id, exc)
                await self.notifications_repository.mark_failed(notification, str(exc))
                await self.notifications_repository.session.commit()
        return delivered
