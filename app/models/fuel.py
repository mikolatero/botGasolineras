from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Fuel(Base):
    __tablename__ = "fuels"
    __table_args__ = (
        Index("ix_fuels_code", "code", unique=True),
        Index("ix_fuels_dataset_key", "dataset_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_key: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    current_prices = relationship("StationPriceCurrent", back_populates="fuel")
    watchlists = relationship("UserWatchlist", back_populates="fuel")

