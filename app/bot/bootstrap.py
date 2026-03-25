from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.middleware import RateLimitMiddleware
from app.bot.router import router
from app.config.settings import get_settings


def build_bot() -> Bot:
    settings = get_settings()
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode(settings.bot_default_parse_mode)),
    )


def build_dispatcher() -> Dispatcher:
    settings = get_settings()
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.message.middleware(RateLimitMiddleware(settings.rate_limit_window_seconds, settings.rate_limit_max_events))
    dispatcher.callback_query.middleware(RateLimitMiddleware(settings.rate_limit_window_seconds, settings.rate_limit_max_events))
    dispatcher.include_router(router)
    return dispatcher

