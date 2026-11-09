"""Anthropic Claude adapter (official ``anthropic`` Python SDK, streaming Messages API)."""
from __future__ import annotations

from collections.abc import AsyncIterator

import anthropic

from .base import (
    GenerationRequest,
    ProviderAdapter,
    ProviderError,
    ProviderInfo,
    StreamEvent,
    merge_consecutive,
)

# Models that accept Anthropic's server-side refusal fallback (beta). When a safety classifier
# declines a request, the API transparently retries on a suitable model instead of returning
# an empty refusal. Other models use the standard endpoint.
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _map_error(exc: Exception) -> ProviderError:
    if isinstance(exc, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
        return ProviderError("Anthropic rejected the API key.", status=getattr(exc, "status_code", None))
    if isinstance(exc, anthropic.NotFoundError):
        return ProviderError("Anthropic model not found.", status=404)
    if isinstance(exc, anthropic.RateLimitError):
        return ProviderError("Anthropic rate limit hit.", retryable=True, status=429)
    if isinstance(exc, anthropic.APIStatusError):
        return ProviderError(
            f"Anthropic API error {exc.status_code}: {exc.message}",
            retryable=exc.status_code >= 500,
            status=exc.status_code,
        )
    if isinstance(exc, anthropic.APIConnectionError):
        return ProviderError("Could not reach the Anthropic API.", retryable=True)
    return ProviderError(f"Anthropic error: {exc}")


class AnthropicAdapter(ProviderAdapter):
    info = ProviderInfo(
        id="anthropic",
        display_name="Anthropic Claude",
        integration="hosted",
        requires_api_key=True,
        suggested_models=["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1"],
        docs_url="https://docs.claude.com/en/api/messages",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url  # override for gateways/proxies (and wire-level tests)

    def _client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        if not api_key:
            raise ProviderError("No Anthropic API key configured.")
        # Retries are handled by the orchestrator so they are visible in the timeline.
        return anthropic.AsyncAnthropic(api_key=api_key, base_url=self.base_url, max_retries=0, timeout=300.0)

    async def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        client = self._client(api_key)
        messages = [{"role": m.role, "content": m.content} for m in merge_consecutive(request.messages)]
        kwargs = dict(model=request.model, max_tokens=request.max_output_tokens, system=request.system,
                      messages=messages)
        try:
            if request.model in _FALLBACK_MODELS:
                manager = client.beta.messages.stream(**kwargs, betas=[_FALLBACK_BETA], fallbacks="default")
            else:
                manager = client.messages.stream(**kwargs)
            async with manager as stream:
                async for text in stream.text_stream:
                    if text:
                        yield StreamEvent(type="text", text=text)
                final = await stream.get_final_message()
        except anthropic.AnthropicError as exc:
            raise _map_error(exc) from exc
        finally:
            await client.close()

        if final.stop_reason == "refusal":
            raise ProviderError("Claude declined this request (stop_reason=refusal).")
        yield StreamEvent(
            type="usage",
            input_tokens=final.usage.input_tokens or 0,
            output_tokens=final.usage.output_tokens or 0,
            stop_reason=final.stop_reason,
        )

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        client = self._client(api_key)
        try:
            page = await client.models.list(limit=100)
            return [m.id for m in page.data]
        except anthropic.AnthropicError as exc:
            raise _map_error(exc) from exc
        finally:
            await client.close()
