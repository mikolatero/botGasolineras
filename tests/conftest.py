from __future__ import annotations

import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.models import Base
from app.repositories.fuels import FuelsRepository


@pytest_asyncio.fixture()
async def session_factory(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

    async with factory() as session:
        await FuelsRepository(session).seed_defaults()
        await session.commit()

    try:
        yield factory
    finally:
        await engine.dispose()

