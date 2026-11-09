"""Request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORM):
    id: str
    email: str
    name: str
    is_admin: bool
    plan_code: str
    subscription_status: str
    credits_usd: float


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---- providers / credentials
class CredentialIn(BaseModel):
    """A provider connection: an API key and/or a base URL (Ollama host, custom server…)."""

    provider: str
    api_key: str = Field(default="", max_length=500)
    base_url: str | None = Field(default=None, max_length=512)
    label: str = Field(default="default", max_length=64)
    verify: bool = True

    @field_validator("base_url")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        v = (v or "").strip().rstrip("/")
        return v or None


class CredentialOut(ORM):
    id: str
    provider: str
    label: str
    key_hint: str
    base_url: str | None
    verified_at: datetime | None
    created_at: datetime


# ---- projects
class ProjectSettings(BaseModel):
    mode: Literal["open_discussion", "structured_delegation", "parallel", "debate", "independent_review"] = \
        "open_discussion"
    approve_delegations: bool = False
    max_turns_per_agent: int = Field(default=8, ge=1, le=100)
    max_agent_messages: int = Field(default=30, ge=0, le=1000)
    max_run_seconds: int = Field(default=600, ge=30, le=86_400)
    max_output_tokens: int = Field(default=2048, ge=256, le=32_000)
    budget_usd: float = Field(default=2.0, ge=0.0, le=10_000)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    shared_context: str = Field(default="", max_length=50_000)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    shared_context: str | None = Field(default=None, max_length=50_000)
    settings: ProjectSettings | None = None


class ProjectOut(ORM):
    id: str
    name: str
    description: str
    shared_context: str
    settings: dict[str, Any]
    created_at: datetime


class FileIn(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    content: str = Field(default="", max_length=200_000)
    shared_with_agents: bool = True

    @field_validator("path")
    @classmethod
    def _safe_path(cls, v: str) -> str:
        v = v.strip().lstrip("/")
        if ".." in v.split("/") or "\\" in v or not v:
            raise ValueError("Invalid path")
        return v


class FileOut(ORM):
    id: str
    path: str
    content: str
    shared_with_agents: bool
    updated_at: datetime


# ---- agents
class AgentIn(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _\-\.]*$")
    role: str = Field(default="", max_length=120)
    instructions: str = Field(default="", max_length=20_000)
    kind: Literal["hosted", "external"] = "hosted"
    provider: str
    model: str = Field(min_length=1, max_length=128)
    credential_id: str | None = None
    external_url: str | None = Field(default=None, max_length=512)
    parent_id: str | None = None

    @field_validator("name")
    @classmethod
    def _reserved(cls, v: str) -> str:
        if v.strip().lower() in {"all", "commander", "plato", "system"}:
            raise ValueError("That name is reserved")
        return v.strip()


class AgentPatch(BaseModel):
    role: str | None = Field(default=None, max_length=120)
    instructions: str | None = Field(default=None, max_length=20_000)
    model: str | None = Field(default=None, max_length=128)
    credential_id: str | None = None
    is_active: bool | None = None


class AgentOut(ORM):
    id: str
    project_id: str
    parent_id: str | None
    name: str
    role: str
    instructions: str
    kind: str
    provider: str
    model: str
    credential_id: str | None
    external_url: str | None
    is_active: bool
    created_at: datetime


# ---- runs
class RunIn(BaseModel):
    objective: str = Field(min_length=1, max_length=20_000)
    mode: str | None = None
    limits: dict[str, float] = Field(default_factory=dict)
    assignments: dict[str, str] = Field(default_factory=dict)  # agent_id -> assignment text

    @field_validator("limits")
    @classmethod
    def _limits(cls, v: dict[str, float]) -> dict[str, float]:
        allowed = {"max_turns_per_agent", "max_agent_messages", "max_run_seconds", "max_output_tokens", "budget_usd"}
        bad = set(v) - allowed
        if bad:
            raise ValueError(f"Unknown limit(s): {', '.join(sorted(bad))}")
        if any(x < 0 for x in v.values()):
            raise ValueError("Limits must be non-negative")
        return v


class RunOut(ORM):
    id: str
    project_id: str
    objective: str
    mode: str
    status: str
    stop_reason: str | None
    limits: dict[str, Any]
    cost_usd: float
    input_tokens: int
    output_tokens: int
    created_at: datetime
    ended_at: datetime | None


class EventOut(ORM):
    seq: int
    type: str
    run_id: str
    project_id: str
    agent_id: str | None
    data: dict[str, Any]
    created_at: datetime


class TaskOut(ORM):
    id: str
    run_id: str
    title: str
    description: str
    assignee_agent_id: str
    created_by_agent_id: str | None
    status: str
    result: str
    created_at: datetime
    updated_at: datetime


class CommanderMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    to: list[str] | None = None  # agent ids; None = all primary agents


# ---- billing
class PlanOut(ORM):
    code: str
    name: str
    price_usd_month: float
    entitlements: dict[str, Any]
    stripe_price_id: str | None


class PlanPatch(BaseModel):
    name: str | None = None
    price_usd_month: float | None = Field(default=None, ge=0)
    stripe_price_id: str | None = None
    entitlements: dict[str, Any] | None = None


class CheckoutIn(BaseModel):
    plan_code: str
