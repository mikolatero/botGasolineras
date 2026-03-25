from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Enum, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.models.base import BIGINT_PK, Base
from app.models.enums import SyncRunStatus


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        Index("ix_sync_runs_status", "status"),
        Index("ix_sync_runs_dataset_timestamp", "dataset_timestamp"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    status: Mapped[SyncRunStatus] = mapped_column(
        Enum(SyncRunStatus, native_enum=False, length=20),
        nullable=False,
        default=SyncRunStatus.RUNNING,
        server_default=SyncRunStatus.RUNNING.value,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stations_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price_rows_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price_rows_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price_drops_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
