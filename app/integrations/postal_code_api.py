from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.config.settings import Settings
from app.integrations.http_client import build_async_client_kwargs
from app.utils.parsing import digits_only

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PostalCodeResolution:
    postal_code: str | None
    checked: bool


class CartoCiudadPostalCodeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.postal_code_geocoder_enabled
        self.url = settings.postal_code_geocoder_url
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
