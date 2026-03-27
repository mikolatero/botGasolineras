from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    outbound_http_trust_env: bool = Field(False, alias="OUTBOUND_HTTP_TRUST_ENV")
    outbound_http_ca_bundle: str | None = Field(None, alias="OUTBOUND_HTTP_CA_BUNDLE")
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    database_url: str = Field(..., alias="DATABASE_URL")
    minetur_api_url: str = Field(
        "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/",
        alias="MINETUR_API_URL",
    )
    minetur_api_timeout_seconds: int = Field(30, alias="MINETUR_API_TIMEOUT_SECONDS")
    minetur_api_retries: int = Field(6, alias="MINETUR_API_RETRIES")
    postal_code_geocoder_enabled: bool = Field(True, alias="POSTAL_CODE_GEOCODER_ENABLED")
    postal_code_geocoder_url: str = Field(
        "https://www.cartociudad.es/geocoder/api/geocoder/reverseGeocode",
        alias="POSTAL_CODE_GEOCODER_URL",
    )
    postal_code_geocoder_timeout_seconds: int = Field(5, alias="POSTAL_CODE_GEOCODER_TIMEOUT_SECONDS")
    postal_code_geocoder_batch_size: int = Field(250, alias="POSTAL_CODE_GEOCODER_BATCH_SIZE")
    postal_code_geocoder_concurrency: int = Field(5, alias="POSTAL_CODE_GEOCODER_CONCURRENCY")
    sync_interval_minutes: int = Field(30, alias="SYNC_INTERVAL_MINUTES")
    run_sync_on_startup: bool = Field(True, alias="RUN_SYNC_ON_STARTUP")
    search_result_page_size: int = Field(5, alias="SEARCH_RESULT_PAGE_SIZE")
    watchlist_page_size: int = Field(5, alias="WATCHLIST_PAGE_SIZE")
    rate_limit_window_seconds: int = Field(3, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_max_events: int = Field(6, alias="RATE_LIMIT_MAX_EVENTS")
    bot_default_parse_mode: str = Field("HTML", alias="BOT_DEFAULT_PARSE_MODE")
    timezone: str = Field("Europe/Madrid", alias="TIMEZONE")

    @property
    def alembic_database_url(self) -> str:
        if self.database_url.startswith("mysql+asyncmy://"):
            return self.database_url.replace("mysql+asyncmy://", "mysql+pymysql://", 1)
        if self.database_url.startswith("sqlite+aiosqlite://"):
            return self.database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
