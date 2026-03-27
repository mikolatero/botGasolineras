from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.config.settings import Settings
from app.integrations.http_client import build_async_client_kwargs
from app.utils.parsing import digits_only, parse_coordinate

logger = logging.getLogger(__name__)


_JSONP_RE = re.compile(r"^[^(]+\((.*)\)\s*;?\s*$", re.DOTALL)


@dataclass(slots=True)
class PostalCodeResolution:
    postal_code: str | None
    checked: bool


class CartoCiudadPostalCodeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.postal_code_geocoder_enabled
        self.url = settings.postal_code_geocoder_url
        self.find_url = f"{self.url.rsplit('/', 1)[0]}/findJsonp"
        self.candidates_url = f"{self.url.rsplit('/', 1)[0]}/candidatesJsonp"
        self.timeout_seconds = settings.postal_code_geocoder_timeout_seconds
        self.batch_size = max(settings.postal_code_geocoder_batch_size, 0)
        self.concurrency = max(settings.postal_code_geocoder_concurrency, 1)

    async def resolve_postal_codes(
        self,
        stations: Sequence[tuple[str, Decimal, Decimal]],
    ) -> dict[str, PostalCodeResolution]:
        if not self.enabled or not stations:
            return {}

        timeout = httpx.Timeout(self.timeout_seconds)
        semaphore = asyncio.Semaphore(self.concurrency)

        client_kwargs = build_async_client_kwargs(self.settings, timeout=timeout, follow_redirects=True)
        async with httpx.AsyncClient(**client_kwargs) as client:

            async def resolve_one(station_id: str, latitude: Decimal, longitude: Decimal) -> tuple[str, PostalCodeResolution]:
                async with semaphore:
                    try:
                        response = await client.get(
                            self.url,
                            params={"lat": format(latitude, "f"), "lon": format(longitude, "f")},
                            headers={"Accept": "application/json"},
                        )
                        if response.status_code == httpx.codes.NO_CONTENT:
                            return station_id, PostalCodeResolution(postal_code=None, checked=True)
                        response.raise_for_status()
                        payload = response.json()
                        if not isinstance(payload, dict):
                            raise ValueError("Postal code geocoder response is not a JSON object")
                        postal_code = digits_only(str(payload.get("postalCode") or ""))
                        if postal_code and len(postal_code) < 5:
                            postal_code = postal_code.zfill(5)
                        return station_id, PostalCodeResolution(postal_code=postal_code, checked=True)
                    except (httpx.HTTPError, ValueError) as exc:
                        logger.warning("Postal code lookup failed for station %s: %s", station_id, exc)
                        return station_id, PostalCodeResolution(postal_code=None, checked=False)

            pairs = await asyncio.gather(*(resolve_one(*station) for station in stations))
        return dict(pairs)

    async def geocode_postal_code(self, postal_code: str) -> tuple[Decimal, Decimal] | None:
        if not self.enabled:
            return None

        normalized_postal_code = digits_only(postal_code)
        if normalized_postal_code is None:
            return None

        timeout = httpx.Timeout(self.timeout_seconds)
        client_kwargs = build_async_client_kwargs(self.settings, timeout=timeout, follow_redirects=True)
        async with httpx.AsyncClient(**client_kwargs) as client:
            for url, params in (
                (self.find_url, {"q": normalized_postal_code}),
                (self.candidates_url, {"q": normalized_postal_code, "limit": 1}),
            ):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == httpx.codes.NO_CONTENT:
                        continue
                    response.raise_for_status()
                    coordinates = self._extract_coordinates(self._parse_json_or_jsonp(response))
                    if coordinates is not None:
                        return coordinates
                except (httpx.HTTPError, ValueError) as exc:
                    logger.warning("Postal code geocoding failed for %s via %s: %s", normalized_postal_code, url, exc)
        return None

    @classmethod
    def _extract_coordinates(cls, payload: object) -> tuple[Decimal, Decimal] | None:
        if isinstance(payload, dict):
            latitude = cls._extract_coordinate_value(payload, _LATITUDE_KEYS)
            longitude = cls._extract_coordinate_value(payload, _LONGITUDE_KEYS)
            if latitude is not None and longitude is not None:
                return latitude, longitude
            for value in payload.values():
                coordinates = cls._extract_coordinates(value)
                if coordinates is not None:
                    return coordinates
            return None
        if isinstance(payload, list):
            for item in payload:
                coordinates = cls._extract_coordinates(item)
                if coordinates is not None:
                    return coordinates
        return None

    @staticmethod
    def _extract_coordinate_value(payload: dict[str, object], keys: tuple[str, ...]) -> Decimal | None:
        lowered = {key.casefold(): value for key, value in payload.items()}
        for key in keys:
            value = lowered.get(key.casefold())
            if value is not None:
                return parse_coordinate(str(value))
        return None

    @staticmethod
    def _parse_json_or_jsonp(response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError:
            match = _JSONP_RE.match(response.text.strip())
            if match is None:
                raise
            return json.loads(match.group(1))


_LATITUDE_KEYS = ("lat", "latitude", "latitud", "y", "LATITUD_WGS84_4326")
_LONGITUDE_KEYS = ("lon", "lng", "longitude", "longitud", "x", "LONGITUD_WGS84_4326")
