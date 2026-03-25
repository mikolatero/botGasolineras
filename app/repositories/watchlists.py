from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import joinedload

from app.models.enums import WatchlistStatus
from app.models.watchlist import UserWatchlist
from app.repositories.base import Repository


class WatchlistsRepository(Repository):
    async def create_or_reactivate(self, user_id: int, station_id: str, fuel_id: int) -> tuple[UserWatchlist, bool]:
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.station_id == station_id,
            UserWatchlist.fuel_id == fuel_id,
        )
        result = await self.session.execute(stmt)
        watchlist = result.scalar_one_or_none()
        created = False

        if watchlist is None:
            watchlist = UserWatchlist(
                user_id=user_id,
                station_id=station_id,
                fuel_id=fuel_id,
                status=WatchlistStatus.ACTIVE,
            )
            self.session.add(watchlist)
            created = True
        else:
            watchlist.status = WatchlistStatus.ACTIVE
            watchlist.paused_at = None

        await self.session.flush()
        return watchlist, created

    async def list_by_user(self, user_id: int, page: int, page_size: int) -> tuple[list[UserWatchlist], int]:
        count_stmt = select(func.count(UserWatchlist.id)).where(UserWatchlist.user_id == user_id)
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = (
            select(UserWatchlist)
            .options(joinedload(UserWatchlist.station), joinedload(UserWatchlist.fuel))
            .where(UserWatchlist.user_id == user_id)
            .order_by(UserWatchlist.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def get_for_user(self, user_id: int, watchlist_id: int) -> UserWatchlist | None:
        stmt = (
            select(UserWatchlist)
            .options(joinedload(UserWatchlist.station), joinedload(UserWatchlist.fuel))
            .where(UserWatchlist.id == watchlist_id, UserWatchlist.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def pause(self, watchlist: UserWatchlist, paused_at: datetime) -> None:
        watchlist.status = WatchlistStatus.PAUSED
        watchlist.paused_at = paused_at
        await self.session.flush()

    async def resume(self, watchlist: UserWatchlist) -> None:
        watchlist.status = WatchlistStatus.ACTIVE
        watchlist.paused_at = None
        await self.session.flush()

    async def delete(self, watchlist: UserWatchlist) -> None:
        await self.session.delete(watchlist)
        await self.session.flush()

    async def list_active_for_pairs(self, pairs: list[tuple[str, int]]) -> dict[tuple[str, int], list[UserWatchlist]]:
        if not pairs:
            return {}
        stmt = (
            select(UserWatchlist)
            .options(joinedload(UserWatchlist.user), joinedload(UserWatchlist.station), joinedload(UserWatchlist.fuel))
            .where(
                UserWatchlist.status == WatchlistStatus.ACTIVE,
                tuple_(UserWatchlist.station_id, UserWatchlist.fuel_id).in_(pairs),
            )
        )
        result = await self.session.execute(stmt)
        grouped: dict[tuple[str, int], list[UserWatchlist]] = defaultdict(list)
        for item in result.scalars().unique().all():
            grouped[(item.station_id, item.fuel_id)].append(item)
        return grouped

    async def mark_notified(self, watchlist: UserWatchlist, price: Decimal, notified_at: datetime) -> None:
        watchlist.last_notified_price = price
        watchlist.last_notification_at = notified_at
        await self.session.flush()
