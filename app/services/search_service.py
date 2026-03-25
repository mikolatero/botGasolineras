from __future__ import annotations

from dataclasses import dataclass

from app.repositories.stations import StationsRepository


@dataclass(slots=True)
class SearchFilters:
    postal_code: str | None = None
    province: str | None = None
    municipality: str | None = None
    locality: str | None = None
    brand: str | None = None
    address_text: str | None = None
    fuel_id: int | None = None

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "postal_code": self.postal_code,
            "province": self.province,
            "municipality": self.municipality,
            "locality": self.locality,
            "brand": self.brand,
            "address_text": self.address_text,
            "fuel_id": self.fuel_id,
        }


class SearchService:
    def __init__(self, stations_repository: StationsRepository) -> None:
        self.stations_repository = stations_repository

    async def search(self, filters: SearchFilters, page: int, page_size: int):
        return await self.stations_repository.search(page=page, page_size=page_size, **filters.as_dict())

    async def list_station_fuels(self, ideess: str):
        return await self.stations_repository.list_station_fuels(ideess)

