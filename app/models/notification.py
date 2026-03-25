from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.models.base import BIGINT_PK, Base
from app.models.enums import NotificationStatus


class NotificationSent(Base):
    __tablename__ = "notifications_sent"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "sync_run_id", name="uq_notifications_sent_watchlist_sync"),
        Index("ix_notifications_sent_status", "status"),
        Index("ix_notifications_sent_station_fuel", "station_id", "fuel_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("user_watchlists.id", ondelete="CASCADE"), nullable=False)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id", ondelete="CASCADE"), nullable=False)
    station_id: Mapped[str] = mapped_column(ForeignKey("stations.ideess", ondelete="CASCADE"), nullable=False)
    fuel_id: Mapped[int] = mapped_column(ForeignKey("fuels.id", ondelete="CASCADE"), nullable=False)
    previous_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    dataset_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, native_enum=False, length=20),
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    watchlist = relationship("UserWatchlist", back_populates="notifications")
    station = relationship("Station")
    fuel = relationship("Fuel")
