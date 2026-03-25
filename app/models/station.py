from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Station(Base, TimestampMixin):
    __tablename__ = "stations"
    __table_args__ = (
        Index("ix_stations_postal_code", "postal_code"),
        Index("ix_stations_municipality", "municipality_normalized"),
        Index("ix_stations_province", "province_normalized"),
        Index("ix_stations_brand", "brand_normalized"),
        Index("ix_stations_locality", "locality_normalized"),
        Index("ix_stations_address", "address_normalized"),
        Index(
            "ft_stations_search",
            "brand",
            "address",
            "municipality",
            "locality",
            mysql_prefix="FULLTEXT",
        ),
    )

    ideess: Mapped[str] = mapped_column(String(16), primary_key=True)
    postal_code: Mapped[str | None] = mapped_column(String(10))
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    address_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    locality: Mapped[str | None] = mapped_column(String(255))
    locality_normalized: Mapped[str | None] = mapped_column(String(255))
    municipality: Mapped[str] = mapped_column(String(255), nullable=False)
    municipality_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    province: Mapped[str] = mapped_column(String(255), nullable=False)
    province_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule: Mapped[str | None] = mapped_column(Text)
    margin: Mapped[str | None] = mapped_column(String(50))
    sale_type: Mapped[str | None] = mapped_column(String(50))
    remision: Mapped[str | None] = mapped_column(String(100))
    locality_code: Mapped[str | None] = mapped_column(String(10))
    province_code: Mapped[str | None] = mapped_column(String(10))
    autonomous_region_code: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    current_prices = relationship("StationPriceCurrent", back_populates="station", cascade="all, delete-orphan")
    watchlists = relationship("UserWatchlist", back_populates="station")

