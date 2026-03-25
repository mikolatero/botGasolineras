from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.models.base import BIGINT_PK, Base


class StationPriceCurrent(Base):
    __tablename__ = "station_prices_current"
    __table_args__ = (
        Index("ix_station_prices_current_station_fuel", "station_id", "fuel_id", unique=True),
        Index("ix_station_prices_current_price", "current_price"),
    )

    station_id: Mapped[str] = mapped_column(ForeignKey("stations.ideess", ondelete="CASCADE"), primary_key=True)
    fuel_id: Mapped[int] = mapped_column(ForeignKey("fuels.id", ondelete="CASCADE"), primary_key=True)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    dataset_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    station = relationship("Station", back_populates="current_prices")
    fuel = relationship("Fuel", back_populates="current_prices")


class StationPriceHistory(Base):
    __tablename__ = "station_price_history"
    __table_args__ = (
        Index("ix_station_price_history_station_fuel", "station_id", "fuel_id"),
        UniqueConstraint("station_id", "fuel_id", "sync_run_id", name="uq_station_price_history_sync"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(ForeignKey("stations.ideess", ondelete="CASCADE"), nullable=False)
    fuel_id: Mapped[int] = mapped_column(ForeignKey("fuels.id", ondelete="CASCADE"), nullable=False)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id", ondelete="CASCADE"), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    dataset_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
