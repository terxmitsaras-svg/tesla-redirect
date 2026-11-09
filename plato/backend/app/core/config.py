"""Application configuration, loaded from environment variables (prefix ``PLATO_``)."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATO_", env_file=".env", extra="ignore")

    env: str = "development"  # development | test | production
    database_url: str = "sqlite+aiosqlite:///./plato.db"
    redis_url: str | None = None  # when set, the event bus fans out through Redis pub/sub

    # Security
    jwt_secret: str = "dev-insecure-change-me-0123456789abcdef"
    jwt_ttl_minutes: int = 60 * 12
    # Fernet key (urlsafe base64, 32 bytes). Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str | None = None
    # NoDecode: accept comma-separated values (or a JSON list) instead of requiring JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])
    admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Providers
    enable_mock_provider: bool = True  # offline, clearly-labelled simulated provider
    allow_private_external_agents: bool = False  # allow external agent URLs on private networks (local dev)
    platform_openai_key: str | None = None
    platform_anthropic_key: str | None = None
    platform_xai_key: str | None = None
    platform_gemini_key: str | None = None
    # JSON object {"model-id": [input_usd_per_mtok, output_usd_per_mtok]} overriding built-in prices
    model_pricing_json: str | None = None

    # Orchestration defaults (per-run overrides are clamped to plan entitlements)
    default_max_turns_per_agent: int = 8
    default_max_agent_messages: int = 30
    default_max_run_seconds: int = 600
    default_max_output_tokens: int = 2048
    default_run_budget_usd: float = 2.0

    # Stripe
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_meter_event_name: str | None = None  # optional Stripe Billing Meter for platform-credit usage
    public_app_url: str = "http://localhost:3000"

    @field_validator("cors_origins", "admin_emails", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def platform_key(self, provider: str) -> str | None:
        return {
            "openai": self.platform_openai_key,
            "anthropic": self.platform_anthropic_key,
            "xai": self.platform_xai_key,
            "gemini": self.platform_gemini_key,
        }.get(provider)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_production:
        if s.jwt_secret.startswith("dev-insecure") or not s.encryption_key:
            raise RuntimeError("PLATO_JWT_SECRET and PLATO_ENCRYPTION_KEY must be set in production")
        if s.enable_mock_provider:
            raise RuntimeError("Disable PLATO_ENABLE_MOCK_PROVIDER in production")
    return s
