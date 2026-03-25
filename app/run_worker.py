from __future__ import annotations

import asyncio

from app.bot.bootstrap import build_bot
from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.scheduler.runner import WorkerRunner


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    bot = build_bot()
    runner = WorkerRunner(bot)
    await runner.start()
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
