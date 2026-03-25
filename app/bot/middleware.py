from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, window_seconds: int, max_events: int) -> None:
        self.window_seconds = window_seconds
        self.max_events = max_events
        self.events: dict[int, deque[float]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        queue = self.events[user_id]
        while queue and now - queue[0] > self.window_seconds:
            queue.popleft()
        if len(queue) >= self.max_events:
            if isinstance(event, Message):
                await event.answer("Demasiadas acciones seguidas. Espera unos segundos.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Demasiadas acciones seguidas. Espera unos segundos.", show_alert=False)
            return None
        queue.append(now)
        return await handler(event, data)

