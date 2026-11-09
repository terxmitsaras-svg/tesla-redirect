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


@dataclass(slots=True)
class ProviderInfo:
    id: str
    display_name: str
    integration: Integration
    requires_api_key: bool
    suggested_models: list[str] = field(default_factory=list)
    docs_url: str = ""


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
