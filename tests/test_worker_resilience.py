from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import httpx
import pytest

from app.integrations.fuel_api import MineturApiClient
from app.integrations.postal_code_api import CartoCiudadPostalCodeClient
from app.scheduler.runner import WorkerRunner


class _FakeAsyncClient:
    def __init__(self, *, errors: list[Exception]) -> None:
        self.errors = list(errors)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, headers=None):
        raise self.errors.pop(0)


class _FakeOkResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"Fecha": "27/03/2026 09:30:00", "ListaEESSPrecio": []}


@pytest.mark.asyncio
async def test_fuel_api_reports_error_type_when_connect_error_has_no_message(monkeypatch) -> None:
    settings = SimpleNamespace(
        minetur_api_url="https://example.com/dataset",
        minetur_api_timeout_seconds=5,
        minetur_api_retries=2,
        minetur_api_enable_curl_fallback=False,
        outbound_http_trust_env=False,
        outbound_http_ca_bundle=None,
    )
    client = MineturApiClient(settings)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(errors=[httpx.ConnectError(""), httpx.ConnectError("")]),
    )

    async def _fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    with pytest.raises(RuntimeError, match="ConnectError: no error message provided"):
        await client.fetch_dataset()


def test_postal_code_api_parses_jsonp_payload() -> None:
    response = httpx.Response(
        200,
        text='callback({"lat":"37.9800000","lon":"-1.1200000"})',
        request=httpx.Request("GET", "https://example.com"),
    )

    payload = CartoCiudadPostalCodeClient._parse_json_or_jsonp(response)

    assert payload == {"lat": "37.9800000", "lon": "-1.1200000"}


@pytest.mark.asyncio
async def test_fuel_api_uses_explicit_http_client_configuration(monkeypatch) -> None:
    captured_kwargs = {}

    class _RecordingAsyncClient:
        def __init__(self, **kwargs) -> None:
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            return _FakeOkResponse()

    settings = SimpleNamespace(
        minetur_api_url="https://example.com/dataset",
        minetur_api_timeout_seconds=5,
        minetur_api_retries=1,
        minetur_api_enable_curl_fallback=False,
        outbound_http_trust_env=False,
        outbound_http_ca_bundle="/etc/ssl/certs/ca-certificates.crt",
    )
    client = MineturApiClient(settings)

    monkeypatch.setattr(httpx, "AsyncClient", _RecordingAsyncClient)

    payload = await client.fetch_dataset()

    assert payload["ListaEESSPrecio"] == []
    assert captured_kwargs["trust_env"] is False
    assert captured_kwargs["verify"] == "/etc/ssl/certs/ca-certificates.crt"


@pytest.mark.asyncio
async def test_fuel_api_falls_back_to_curl_when_httpx_connect_fails(monkeypatch) -> None:
    settings = SimpleNamespace(
        minetur_api_url="https://example.com/dataset",
        minetur_api_timeout_seconds=5,
        minetur_api_retries=1,
        minetur_api_enable_curl_fallback=True,
        outbound_http_trust_env=False,
        outbound_http_ca_bundle=None,
    )
    client = MineturApiClient(settings)

    async def _fail_httpx(*, headers):
        raise httpx.ConnectError("")

    async def _ok_curl(*, headers):
        return {"Fecha": "27/03/2026 09:30:00", "ListaEESSPrecio": []}

    monkeypatch.setattr(client, "_fetch_dataset_via_httpx", _fail_httpx)
    monkeypatch.setattr(client, "_fetch_dataset_via_curl", _ok_curl)

    payload = await client.fetch_dataset()

    assert payload["ListaEESSPrecio"] == []


@pytest.mark.asyncio
async def test_startup_task_callback_logs_error_instead_of_leaking_task_exception(caplog) -> None:
    loop = asyncio.get_running_loop()
    task = loop.create_future()
    task.set_exception(RuntimeError("boom"))

    with caplog.at_level(logging.ERROR):
        WorkerRunner._log_startup_task_result(task)

    assert "Initial startup sync failed" in caplog.text
