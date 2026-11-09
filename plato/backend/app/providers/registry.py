"""Provider registry. Register a new adapter here — the orchestrator needs no changes."""
from __future__ import annotations

from ..core.config import get_settings
from .anthropic_adapter import AnthropicAdapter
from .base import ProviderAdapter, ProviderError
from .external_adapter import ExternalAgentAdapter
from .gemini_adapter import GeminiAdapter
from .mock_adapter import MockAdapter
from .openai_adapter import openai_adapter, xai_adapter

_REGISTRY: dict[str, ProviderAdapter] = {}


def _build() -> dict[str, ProviderAdapter]:
    adapters: list[ProviderAdapter] = [
        openai_adapter(), AnthropicAdapter(), xai_adapter(), GeminiAdapter(), ExternalAgentAdapter()
    ]
    if get_settings().enable_mock_provider:
        adapters.append(MockAdapter())
    return {a.info.id: a for a in adapters}


def registry() -> dict[str, ProviderAdapter]:
    if not _REGISTRY:
        _REGISTRY.update(_build())
    return _REGISTRY


def get_adapter(provider: str) -> ProviderAdapter:
    try:
        return registry()[provider]
    except KeyError as exc:
        raise ProviderError(f"Unknown or disabled provider: {provider}") from exc


def register_adapter(adapter: ProviderAdapter) -> None:
    """Extension point (also used by tests to inject fakes)."""
    registry()[adapter.info.id] = adapter
