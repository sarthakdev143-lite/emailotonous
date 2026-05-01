"""Application settings and shared constants."""

from __future__ import annotations

import logging
from functools import lru_cache
from secrets import token_urlsafe

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOGGER = logging.getLogger(__name__)

API_PREFIX = "/api"
APP_NAME = "Email Wake-Up Agent"
DEFAULT_COMPANY_NAME = "Wake Up Talent"
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./agent.db"
DEFAULT_FROM_EMAIL = "agent@yourdomain.com"
DEFAULT_IMAP_HOST = "imap.gmail.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_IMAP_POLL_INTERVAL_SECONDS = 60
DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8000
DEFAULT_CORS_ORIGINS = ["http://localhost:5173"]
PRODUCTION_ENVIRONMENT = "production"
OPENAI_MODEL = "gpt-4o"
GROQ_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.2
MESSAGE_DIRECTION_INBOUND = "inbound"
MESSAGE_DIRECTION_OUTBOUND = "outbound"
THREAD_STATUS_PENDING = "pending"
THREAD_STATUS_OUTREACH_SENT = "outreach_sent"
THREAD_STATUS_NEGOTIATING = "negotiating"
THREAD_STATUS_SLOT_PROPOSED = "slot_proposed"
THREAD_STATUS_BOOKED = "booked"
THREAD_STATUS_CLOSED_NO_FIT = "closed_no_fit"
THREAD_STATUS_CLOSED_NO_REPLY = "closed_no_reply"
BOOKING_STATUS_CONFIRMED = "confirmed"
BOOKING_STATUS_CANCELLED = "cancelled"
BOOKING_STATUS_RESCHEDULED = "rescheduled"
DEFAULT_REPLY_SUBJECT = "Opportunity follow-up"
DEFAULT_SLOT_COUNT = 3


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    from_email: str = Field(default=DEFAULT_FROM_EMAIL, alias="FROM_EMAIL")
    imap_host: str = Field(default=DEFAULT_IMAP_HOST, alias="IMAP_HOST")
    imap_port: int = Field(default=DEFAULT_IMAP_PORT, alias="IMAP_PORT")
    imap_user: str | None = Field(default=None, alias="IMAP_USER")
    imap_password: str | None = Field(default=None, alias="IMAP_PASSWORD")
    imap_poll_interval_seconds: int = Field(
        default=DEFAULT_IMAP_POLL_INTERVAL_SECONDS,
        alias="IMAP_POLL_INTERVAL_SECONDS",
    )
    database_url: str = Field(default=DEFAULT_DATABASE_URL, alias="DATABASE_URL")
    secret_key: str | None = Field(default=None, alias="SECRET_KEY")
    debug: bool = Field(default=False, alias="DEBUG")
    app_env: str = Field(default="development", alias="APP_ENV")
    company_name: str = Field(default=DEFAULT_COMPANY_NAME, alias="COMPANY_NAME")
    api_host: str = Field(default=DEFAULT_API_HOST, alias="API_HOST")
    api_port: int = Field(default=DEFAULT_API_PORT, alias="API_PORT")
    cors_origins: list[str] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS), alias="CORS_ORIGINS"
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> bool:
        """Normalize debug values from varied environment strings."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"1", "true", "yes", "on", "debug", "development"}
        return bool(value)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Normalize CORS origins from CSV strings or lists."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return list(DEFAULT_CORS_ORIGINS)

    @property
    def llm_provider(self) -> str:
        """Return the active LLM provider name or the Puter fallback."""
        if self.openai_api_key:
            return "openai"
        if self.groq_api_key:
            return "groq"
        return "puter"

    @property
    def llm_available(self) -> bool:
        """Return whether a server-side LLM provider is available."""
        return self.openai_api_key is not None or self.groq_api_key is not None


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    settings = Settings()
    if not settings.secret_key or settings.secret_key == "change-me":
        if settings.app_env == PRODUCTION_ENVIRONMENT:
            LOGGER.error("SECRET_KEY is not configured for production.")
            raise ValueError("SECRET_KEY must be set when APP_ENV=production.")
        generated_secret = token_urlsafe(32)
        LOGGER.warning("SECRET_KEY is unset or placeholder; generated a development secret.")
        settings.secret_key = generated_secret
    return settings
