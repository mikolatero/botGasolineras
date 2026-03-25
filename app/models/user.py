from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PK, Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_telegram_user_id", "telegram_user_id", unique=True),
        Index("ix_users_username", "username"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    watchlists = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
