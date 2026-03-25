from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.models.base import BIGINT_PK, Base, TimestampMixin
from app.models.enums import WatchlistStatus


class UserWatchlist(Base, TimestampMixin):
    __tablename__ = "user_watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "station_id", "fuel_id", name="uq_user_watchlists_target"),
        Index("ix_user_watchlists_status", "status"),
        Index("ix_user_watchlists_station_fuel", "station_id", "fuel_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    station_id: Mapped[str] = mapped_column(ForeignKey("stations.ideess", ondelete="CASCADE"), nullable=False)
    fuel_id: Mapped[int] = mapped_column(ForeignKey("fuels.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[WatchlistStatus] = mapped_column(
        Enum(WatchlistStatus, native_enum=False, length=20),
        nullable=False,
        default=WatchlistStatus.ACTIVE,
        server_default=WatchlistStatus.ACTIVE.value,
    )
    last_notified_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    last_notification_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="watchlists")
    station = relationship("Station", back_populates="watchlists")
    fuel = relationship("Fuel", back_populates="watchlists")
    notifications = relationship("NotificationSent", back_populates="watchlist")
