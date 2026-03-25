from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class MineturApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_dataset(self) -> dict[str, Any]:
        headers = {"Accept": "text/json"}
        timeout = httpx.Timeout(self.settings.minetur_api_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            last_error: Exception | None = None
            for attempt in range(1, self.settings.minetur_api_retries + 1):
                try:
                    response = await client.get(self.settings.minetur_api_url, headers=headers)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError("Dataset root is not a JSON object")
                    return payload
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc
                    logger.warning("Dataset fetch failed on attempt %s/%s: %s", attempt, self.settings.minetur_api_retries, exc)
                    if attempt < self.settings.minetur_api_retries:
                        await asyncio.sleep(min(2**attempt, 10))
            raise RuntimeError(f"Unable to fetch official dataset: {last_error}") from last_error

