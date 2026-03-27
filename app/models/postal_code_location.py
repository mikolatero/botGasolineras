from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PostalCodeLocation(Base, TimestampMixin):
    __tablename__ = "postal_code_locations"
    __table_args__ = (
        Index("ix_postal_code_locations_postal_code", "postal_code", unique=True),
    )

    postal_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
