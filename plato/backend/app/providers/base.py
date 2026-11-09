"""Provider adapter contract.

Every AI backend — a hosted provider API or a user-connected external agent runtime — is
wrapped in a ``ProviderAdapter``. The orchestration engine only ever talks to this interface,
so adding a provider never touches the engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["user", "assistant"]
Integration = Literal["hosted", "external", "simulated"]
# Grouping shown in the UI.
Category = Literal["frontier", "open", "local", "custom"]
# fixed: provider URL is built in. optional: built-in default, user may override (e.g. Ollama host).
# required: user must supply it (e.g. a custom OpenAI-compatible server).
BaseUrlMode = Literal["fixed", "optional", "required"]


@dataclass(slots=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(slots=True)
class GenerationRequest:
    model: str
    system: str
    messages: list[ChatMessage]
    max_output_tokens: int = 4096


@dataclass(slots=True)
class StreamEvent:
    """Streamed unit from a provider: a text delta, or the final usage report."""

    type: Literal["text", "usage"]
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None
    estimated: bool = False  # True when the provider reported no token usage and PLATO estimated it


@dataclass(slots=True)
class ProviderInfo:
    id: str
    display_name: str
    integration: Integration
    requires_api_key: bool
    suggested_models: list[str] = field(default_factory=list)
    docs_url: str = ""
    category: Category = "frontier"
    base_url_mode: BaseUrlMode = "fixed"
    default_base_url: str | None = None
    self_hosted: bool = False  # runs on the user's own hardware: no per-token API charge


class ProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool = False, status: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status = status


class ProviderAdapter(ABC):
    info: ProviderInfo

    @abstractmethod
    def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion. Must yield exactly one ``usage`` event at the end."""

    @abstractmethod
    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        """List models available to this key. Used to verify credentials on connect."""


def merge_consecutive(messages: list[ChatMessage]) -> list[ChatMessage]:
    """Most providers require alternating roles starting with ``user``; merge same-role runs."""
    out: list[ChatMessage] = []
    for m in messages:
        if out and out[-1].role == m.role:
            out[-1] = ChatMessage(m.role, out[-1].content + "\n\n" + m.content)
        else:
            out.append(ChatMessage(m.role, m.content))
    if out and out[0].role != "user":
        out.insert(0, ChatMessage("user", "(conversation start)"))
    return out


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token) for providers that report no usage."""
    return max(1, len(text) // 4) if text else 0
