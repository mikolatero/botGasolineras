from __future__ import annotations

import argparse
import asyncio
import logging

from app.config.database import SessionLocal
from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.integrations.postal_code_api import CartoCiudadPostalCodeClient
from app.services.postal_code_backfill_service import PostalCodeBackfillService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh postal code resolutions in controlled batches.")
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Mark every active station with coordinates as pending for geocoder refresh before starting.",
    )
    parser.add_argument(
        "--clear-resolved",
        action="store_true",
        help="Clear stored resolved postal codes when used together with --reset-all.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=2.0,
        help="Sleep between batches to avoid hammering the geocoder (default: 2.0).",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Maximum number of batches to process in this run. 0 means until the queue is empty.",
    )
    return parser


async def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    async with SessionLocal() as session:
        service = PostalCodeBackfillService(
            session=session,
            postal_code_client=CartoCiudadPostalCodeClient(settings),
        )

        if args.reset_all:
            reset_count = await service.reset_all(clear_resolved=args.clear_resolved)
            logging.getLogger(__name__).info(
                "Postal code backfill queue reset: stations_marked_pending=%s clear_resolved=%s",
                reset_count,
                args.clear_resolved,
            )

        stats = await service.run(
            delay_seconds=args.delay_seconds,
            max_batches=args.max_batches or None,
        )
        logging.getLogger(__name__).info("Postal code backfill completed: %s", stats)


if __name__ == "__main__":
    asyncio.run(main())
