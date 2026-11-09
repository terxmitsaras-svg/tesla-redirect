"""OpenAI adapter (official ``openai`` SDK, streaming Chat Completions).

xAI Grok exposes an OpenAI-compatible API, so it reuses this adapter with a different base URL.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import openai

from .base import (
    GenerationRequest,
    ProviderAdapter,
    ProviderError,
    ProviderInfo,
    StreamEvent,
    merge_consecutive,
)


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(self, info: ProviderInfo, base_url: str | None = None):
        self.info = info
        self.base_url = base_url

    def _client(self, api_key: str | None) -> openai.AsyncOpenAI:
        if not api_key:
            raise ProviderError(f"No {self.info.display_name} API key configured.")
        return openai.AsyncOpenAI(api_key=api_key, base_url=self.base_url, max_retries=0, timeout=300.0)

    def _map_error(self, exc: Exception) -> ProviderError:
        name = self.info.display_name
        if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
            return ProviderError(f"{name} rejected the API key.", status=exc.status_code)
        if isinstance(exc, openai.NotFoundError):
            return ProviderError(f"{name} model not found.", status=404)
        if isinstance(exc, openai.RateLimitError):
            return ProviderError(f"{name} rate limit hit.", retryable=True, status=429)
        if isinstance(exc, openai.APIStatusError):
            return ProviderError(f"{name} API error {exc.status_code}: {exc.message}",
                                 retryable=exc.status_code >= 500, status=exc.status_code)
        if isinstance(exc, openai.APIConnectionError):
            return ProviderError(f"Could not reach the {name} API.", retryable=True)
        return ProviderError(f"{name} error: {exc}")

    async def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        client = self._client(api_key)
        messages = [{"role": "system", "content": request.system}] + [
            {"role": m.role, "content": m.content} for m in merge_consecutive(request.messages)
        ]
        input_tokens = output_tokens = 0
        finish: str | None = None
        try:
            stream = await client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_completion_tokens=request.max_output_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens or 0
                    output_tokens = chunk.usage.completion_tokens or 0
                for choice in chunk.choices or []:
                    if choice.delta and choice.delta.content:
                        yield StreamEvent(type="text", text=choice.delta.content)
                    if choice.finish_reason:
                        finish = choice.finish_reason
        except openai.OpenAIError as exc:
            raise self._map_error(exc) from exc
        finally:
            await client.close()
        yield StreamEvent(type="usage", input_tokens=input_tokens, output_tokens=output_tokens, stop_reason=finish)

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        client = self._client(api_key)
        try:
            page = await client.models.list()
            return sorted(m.id for m in page.data)
        except openai.OpenAIError as exc:
            raise self._map_error(exc) from exc
        finally:
            await client.close()


def openai_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        ProviderInfo(
            id="openai", display_name="OpenAI", integration="hosted", requires_api_key=True,
            suggested_models=[],  # populated live from GET /v1/models when a key is connected
            docs_url="https://platform.openai.com/docs/api-reference/chat",
        )
    )


def xai_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        ProviderInfo(
            id="xai", display_name="xAI Grok", integration="hosted", requires_api_key=True,
            suggested_models=[], docs_url="https://docs.x.ai/docs/api-reference",
        ),
        base_url="https://api.x.ai/v1",
    )
