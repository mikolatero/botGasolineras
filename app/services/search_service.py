from __future__ import annotations

from dataclasses import dataclass

from app.integrations.postal_code_api import CartoCiudadPostalCodeClient
from app.repositories.postal_code_locations import PostalCodeLocationsRepository
from app.repositories.stations import StationsRepository
from app.utils.timezone import now_madrid


@dataclass(slots=True)
class SearchFilters:
    postal_code: str | None = None
    province: str | None = None
    municipality: str | None = None
    locality: str | None = None
    brand: str | None = None
    address_text: str | None = None
    fuel_id: int | None = None
    radius_km: int | None = None

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "postal_code": self.postal_code,
            "radius_km": self.radius_km,
            "province": self.province,
            "municipality": self.municipality,
            "locality": self.locality,
            "brand": self.brand,
            "address_text": self.address_text,
            "fuel_id": self.fuel_id,
        }


class SearchService:
    def __init__(
        self,
        stations_repository: StationsRepository,
        postal_code_locations_repository: PostalCodeLocationsRepository | None = None,
        postal_code_client: CartoCiudadPostalCodeClient | None = None,
    ) -> None:
        self.stations_repository = stations_repository
        self.postal_code_locations_repository = postal_code_locations_repository
        self.postal_code_client = postal_code_client

    async def search(self, filters: SearchFilters, page: int, page_size: int):
        search_kwargs = filters.as_dict()

        if filters.postal_code and filters.radius_km:
            center = await self._get_postal_code_center(filters.postal_code)
            if center is not None:
                search_kwargs["radius_center_latitude"] = float(center[0])
                search_kwargs["radius_center_longitude"] = float(center[1])

        return await self.stations_repository.search(page=page, page_size=page_size, **search_kwargs)

    async def list_station_fuels(self, ideess: str):
        return await self.stations_repository.list_station_fuels(ideess)

    async def _get_postal_code_center(self, postal_code: str):
        if self.postal_code_locations_repository is None or self.postal_code_client is None:
            return None

        cached = await self.postal_code_locations_repository.get(postal_code)
        if cached is not None:
            return cached.latitude, cached.longitude

        coordinates = await self.postal_code_client.geocode_postal_code(postal_code)
        if coordinates is None:
            return None

        await self.postal_code_locations_repository.upsert(
            postal_code=postal_code,
            latitude=coordinates[0],
            longitude=coordinates[1],
            updated_at=now_madrid(),
        )
        return coordinates
