from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config.settings import get_settings


def madrid_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_madrid() -> datetime:
    return datetime.now(tz=madrid_tz())

