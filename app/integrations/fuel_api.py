from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import Mapping
from typing import Any

import httpx

from app.config.settings import Settings
from app.integrations.http_client import build_async_client_kwargs, summarize_exception_chain

logger = logging.getLogger(__name__)


class MineturApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_dataset(self) -> dict[str, Any]:
        headers = {"Accept": "text/json"}
        last_error: Exception | None = None
        for attempt in range(1, self.settings.minetur_api_retries + 1):
            try:
                return await self._fetch_dataset_via_httpx(headers=headers)
            except httpx.ConnectError as exc:
                last_error = exc
                error_summary = summarize_exception_chain(exc)
                logger.warning(
                    "Dataset fetch failed on attempt %s/%s for %s via httpx: %s",
                    attempt,
                    self.settings.minetur_api_retries,
                    self.settings.minetur_api_url,
                    error_summary,
                )
                if self.settings.minetur_api_enable_curl_fallback:
                    try:
                        logger.info("Retrying dataset fetch with curl fallback for %s", self.settings.minetur_api_url)
                        return await self._fetch_dataset_via_curl(headers=headers)
                    except Exception as curl_exc:
                        last_error = curl_exc
                        logger.warning(
                            "Curl fallback failed on attempt %s/%s for %s: %s",
                            attempt,
                            self.settings.minetur_api_retries,
                            self.settings.minetur_api_url,
                            summarize_exception_chain(curl_exc),
                        )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                error_summary = summarize_exception_chain(exc)
                logger.warning(
                    "Dataset fetch failed on attempt %s/%s for %s: %s",
                    attempt,
                    self.settings.minetur_api_retries,
                    self.settings.minetur_api_url,
                    error_summary,
                )
            if attempt < self.settings.minetur_api_retries:
                await asyncio.sleep(self._retry_delay_seconds(attempt))
        error_summary = "unknown error" if last_error is None else summarize_exception_chain(last_error)
        raise RuntimeError(f"Unable to fetch official dataset: {error_summary}") from last_error

    async def _fetch_dataset_via_httpx(self, *, headers: Mapping[str, str]) -> dict[str, Any]:
        timeout = httpx.Timeout(self.settings.minetur_api_timeout_seconds)
        client_kwargs = build_async_client_kwargs(self.settings, timeout=timeout, follow_redirects=True)
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(self.settings.minetur_api_url, headers=dict(headers))
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Dataset root is not a JSON object")
            return payload

    async def _fetch_dataset_via_curl(self, *, headers: Mapping[str, str]) -> dict[str, Any]:
        command = [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            str(self.settings.minetur_api_timeout_seconds),
        ]
        for name, value in headers.items():
            command.extend(["--header", f"{name}: {value}"])
        command.append(self.settings.minetur_api_url)

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            detail = (stderr.decode("utf-8", errors="replace").strip() or f"curl exited with status {process.returncode}")
            raise RuntimeError(f"curl fallback failed: {detail}")

        try:
            payload = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"curl fallback returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Dataset root is not a JSON object")
        return payload

    @staticmethod
    def _retry_delay_seconds(attempt: int) -> float:
        base_delay = min(2**attempt, 30)
        jitter = random.uniform(0, 0.5)
        return base_delay + jitter
