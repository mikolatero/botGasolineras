from __future__ import annotations

import enum


class WatchlistStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class SyncRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

