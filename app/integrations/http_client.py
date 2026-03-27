from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import Settings


def build_async_client_kwargs(
    settings: Settings,
    *,
    timeout: httpx.Timeout,
    follow_redirects: bool = True,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "timeout": timeout,
        "follow_redirects": follow_redirects,
        "trust_env": settings.outbound_http_trust_env,
    }
    if settings.outbound_http_ca_bundle:
        kwargs["verify"] = settings.outbound_http_ca_bundle
    return kwargs


def summarize_exception_chain(exc: BaseException) -> str:
    parts: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        detail = str(current) or "no error message provided"
        parts.append(f"{current.__class__.__name__}: {detail}")
        current = current.__cause__ if isinstance(current.__cause__, BaseException) else None

    return " <- ".join(parts) if parts else "unknown error"
