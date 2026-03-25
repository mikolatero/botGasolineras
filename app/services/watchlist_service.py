from __future__ import annotations

from app.repositories.watchlists import WatchlistsRepository


class WatchlistService:
    def __init__(self, watchlists_repository: WatchlistsRepository) -> None:
        self.watchlists_repository = watchlists_repository

    async def subscribe(self, user_id: int, station_id: str, fuel_id: int):
        return await self.watchlists_repository.create_or_reactivate(user_id, station_id, fuel_id)

    async def list_user_watchlists(self, user_id: int, page: int, page_size: int):
        return await self.watchlists_repository.list_by_user(user_id, page, page_size)

