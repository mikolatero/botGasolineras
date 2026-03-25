from __future__ import annotations

import asyncio

from app.bot.bootstrap import build_bot, build_dispatcher
from app.config.logging import configure_logging
from app.config.settings import get_settings


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    bot = build_bot()
    dispatcher = build_dispatcher()
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

