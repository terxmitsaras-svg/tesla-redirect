"""Application configuration, loaded from environment variables (prefix ``PLATO_``)."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# localhost, *.local (mDNS), ChromeOS Linux (penguin.linux.test), RFC 1918 private networks, and
# 100.64.0.0/10 (CGNAT; used by Tailscale to reach a home server from a phone).
LAN_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1|\[::1\]|[a-z0-9-]+\.local|penguin\.linux\.test"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})(:\d{1,5})?$"
)


class Settings(BaseSettings):
    # plato/.env (written by the install scripts / used by Docker) then backend/.env; later wins.
    # env_ignore_empty: `KEY=` (as in .env.example) means "use the default", not an empty value.
    model_config = SettingsConfigDict(env_prefix="PLATO_", env_file=("../.env", ".env"), extra="ignore",
                                      env_ignore_empty=True, env_file_encoding="utf-8")

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
    # Regex of extra allowed browser origins. Unset = in development, any localhost/LAN origin
    # (phones and other computers on your network); in production, none. Auth uses bearer tokens,
    # not cookies, so this cannot be used for cross-site request forgery.
    cors_origin_regex: str | None = None
    admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Providers
    enable_mock_provider: bool = True  # offline, clearly-labelled simulated provider
    # Allow provider/agent URLs on localhost or private networks (needed for local Ollama / LM Studio).
    # Unset = allowed outside production, blocked in production (SSRF protection for multi-tenant SaaS).
    allow_private_endpoints: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("PLATO_ALLOW_PRIVATE_ENDPOINTS", "PLATO_ALLOW_PRIVATE_EXTERNAL_AGENTS"),
    )
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

    @property
    def effective_cors_origin_regex(self) -> str | None:
        if self.cors_origin_regex is not None:
            return self.cors_origin_regex or None
        if self.is_production:
            return None
        return LAN_ORIGIN_REGEX

    @property
    def private_endpoints_allowed(self) -> bool:
        if self.allow_private_endpoints is not None:
            return self.allow_private_endpoints
        return not self.is_production

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
