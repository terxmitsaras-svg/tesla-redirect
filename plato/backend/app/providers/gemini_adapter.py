"""Google Gemini adapter (official ``google-genai`` SDK, streaming generateContent)."""
from __future__ import annotations

from collections.abc import AsyncIterator

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .base import (
    GenerationRequest,
    ProviderAdapter,
    ProviderError,
    ProviderInfo,
    StreamEvent,
    merge_consecutive,
)


def _map_error(exc: Exception) -> ProviderError:
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None) or 0
        if code in (401, 403):
            return ProviderError("Gemini rejected the API key.", status=code)
        if code == 404:
            return ProviderError("Gemini model not found.", status=404)
        if code == 429:
            return ProviderError("Gemini rate limit hit.", retryable=True, status=429)
        return ProviderError(f"Gemini API error {code}: {exc}", retryable=code >= 500, status=code)
    return ProviderError(f"Gemini error: {exc}", retryable=True)


class GeminiAdapter(ProviderAdapter):
    info = ProviderInfo(
        id="gemini", display_name="Google Gemini", integration="hosted", requires_api_key=True,
        suggested_models=[], docs_url="https://ai.google.dev/api/generate-content",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url  # override for gateways/proxies (and wire-level tests)

    def _client(self, api_key: str | None) -> genai.Client:
        if not api_key:
            raise ProviderError("No Gemini API key configured.")
        opts = types.HttpOptions(base_url=self.base_url) if self.base_url else None
        return genai.Client(api_key=api_key, http_options=opts)

    async def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        client = self._client(api_key)
        contents = [
            types.Content(role="model" if m.role == "assistant" else "user", parts=[types.Part(text=m.content)])
            for m in merge_consecutive(request.messages)
        ]
        config = types.GenerateContentConfig(
            system_instruction=request.system, max_output_tokens=request.max_output_tokens
        )
        input_tokens = output_tokens = 0
        finish: str | None = None
        try:
            stream = await client.aio.models.generate_content_stream(
                model=request.model, contents=contents, config=config
            )
            async for chunk in stream:
                if chunk.usage_metadata:
                    input_tokens = chunk.usage_metadata.prompt_token_count or input_tokens
                    output_tokens = chunk.usage_metadata.candidates_token_count or output_tokens
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    finish = str(chunk.candidates[0].finish_reason)
                text = chunk.text if chunk.candidates else None
                if text:
                    yield StreamEvent(type="text", text=text)
        except genai_errors.APIError as exc:
            raise _map_error(exc) from exc
        yield StreamEvent(type="usage", input_tokens=input_tokens, output_tokens=output_tokens, stop_reason=finish)

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        client = self._client(api_key)
        try:
            out: list[str] = []
            pager = await client.aio.models.list()
            async for m in pager:
                actions = getattr(m, "supported_actions", None) or []
                if not actions or "generateContent" in actions:
                    out.append((m.name or "").removeprefix("models/"))
            return sorted(x for x in out if x)
        except genai_errors.APIError as exc:
            raise _map_error(exc) from exc
