"""OpenAI-compatible adapter (official ``openai`` SDK, streaming Chat Completions).

Many providers and local runtimes expose the OpenAI Chat Completions API: xAI Grok, Hugging Face
Inference Providers, Mistral, Groq, DeepSeek, Together AI, OpenRouter, Ollama, LM Studio, vLLM,
llama.cpp server, LocalAI… They differ in small but breaking ways, so each one is described by a
``CompatProfile`` instead of assuming OpenAI's exact behaviour:

* ``token_param`` — OpenAI requires ``max_completion_tokens`` (reasoning models reject
  ``max_tokens``); most compatible servers only document ``max_tokens``.
* ``stream_usage`` — whether to send ``stream_options.include_usage``. Only enabled where the
  provider documents it; otherwise usage is read from any chunk that carries it (including
  Groq's ``x_groq.usage``) and, if none does, estimated and flagged as estimated.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import openai

from ..core.netguard import UnsafeURLError, validate_endpoint_url
from .base import (
    GenerationRequest,
    ProviderAdapter,
    ProviderError,
    ProviderInfo,
    StreamEvent,
    estimate_tokens,
    merge_consecutive,
)

# Local runtimes ignore the key, but the SDK requires a non-empty value.
_PLACEHOLDER_KEY = "not-needed"


@dataclass(frozen=True)
class CompatProfile:
    token_param: str = "max_tokens"
    stream_usage: bool = False


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(self, info: ProviderInfo, base_url: str | None = None, profile: CompatProfile | None = None):
        self.info = info
        # Explicit base_url (tests, gateways) wins over the catalogue default.
        self.base_url = base_url or info.default_base_url
        self.profile = profile or CompatProfile()

    async def _resolve_base_url(self, endpoint: str | None) -> str | None:
        """User-supplied URLs (Ollama host, custom server) are SSRF-checked; built-in URLs are trusted."""
        if self.info.base_url_mode == "fixed" or not endpoint:
            if self.info.base_url_mode == "required" and not endpoint:
                raise ProviderError(f"{self.info.display_name} needs a base URL. Add it under Providers.")
            base = self.base_url
            if self.info.self_hosted and base:
                await self._check(base)
            return base
        await self._check(endpoint)
        return endpoint.rstrip("/")

    async def _check(self, url: str) -> None:
        try:
            await validate_endpoint_url(url)
        except UnsafeURLError as exc:
            raise ProviderError(f"{self.info.display_name} URL rejected: {exc}") from exc

    def _client(self, api_key: str | None, base_url: str | None) -> openai.AsyncOpenAI:
        if not api_key:
            if self.info.requires_api_key:
                raise ProviderError(f"No {self.info.display_name} API key configured.")
            api_key = _PLACEHOLDER_KEY
        return openai.AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0, timeout=300.0)

    def _map_error(self, exc: Exception) -> ProviderError:
        name = self.info.display_name
        if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
            return ProviderError(f"{name} rejected the API key.", status=exc.status_code)
        if isinstance(exc, openai.NotFoundError):
            return ProviderError(f"{name}: model or endpoint not found.", status=404)
        if isinstance(exc, openai.RateLimitError):
            return ProviderError(f"{name} rate limit hit.", retryable=True, status=429)
        if isinstance(exc, openai.APIStatusError):
            return ProviderError(f"{name} API error {exc.status_code}: {exc.message}",
                                 retryable=exc.status_code >= 500, status=exc.status_code)
        if isinstance(exc, openai.APIConnectionError):
            hint = " Is the server running and reachable from the PLATO API?" if self.info.self_hosted else ""
            return ProviderError(f"Could not reach {name}.{hint}", retryable=True)
        return ProviderError(f"{name} error: {exc}")

    async def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        client = self._client(api_key, await self._resolve_base_url(endpoint))
        messages = [{"role": "system", "content": request.system}] + [
            {"role": m.role, "content": m.content} for m in merge_consecutive(request.messages)
        ]
        kwargs: dict = {"model": request.model, "messages": messages, "stream": True,
                        self.profile.token_param: request.max_output_tokens}
        if self.profile.stream_usage:
            kwargs["stream_options"] = {"include_usage": True}

        input_tokens = output_tokens = 0
        got_usage = False
        finish: str | None = None
        produced: list[str] = []
        try:
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                usage = chunk.usage or _extra_usage(chunk)
                if usage:
                    input_tokens = _get(usage, "prompt_tokens") or input_tokens
                    output_tokens = _get(usage, "completion_tokens") or output_tokens
                    got_usage = True
                for choice in chunk.choices or []:
                    if choice.delta and choice.delta.content:
                        produced.append(choice.delta.content)
                        yield StreamEvent(type="text", text=choice.delta.content)
                    if choice.finish_reason:
                        finish = choice.finish_reason
        except openai.OpenAIError as exc:
            raise self._map_error(exc) from exc
        finally:
            await client.close()

        if not got_usage:
            input_tokens = estimate_tokens("".join(m["content"] for m in messages))
            output_tokens = estimate_tokens("".join(produced))
        yield StreamEvent(type="usage", input_tokens=input_tokens, output_tokens=output_tokens,
                          stop_reason=finish, estimated=not got_usage)

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        client = self._client(api_key, await self._resolve_base_url(endpoint))
        try:
            page = await client.models.list()
            return sorted(m.id for m in page.data)
        except openai.OpenAIError as exc:
            raise self._map_error(exc) from exc
        finally:
            await client.close()


def _get(obj, key: str) -> int:
    return int((obj.get(key) if isinstance(obj, dict) else getattr(obj, key, 0)) or 0)


def _extra_usage(chunk) -> dict | None:
    """Some providers put usage outside the standard field (e.g. Groq: ``x_groq.usage``)."""
    extra = getattr(chunk, "model_extra", None) or {}
    x_groq = extra.get("x_groq")
    if isinstance(x_groq, dict) and isinstance(x_groq.get("usage"), dict):
        return x_groq["usage"]
    return None


# ---------------------------------------------------------------------------------- catalogue
# (info, profile). Suggested models are empty where the live /models list is authoritative.
def _p(id_, name, *, category, url, key=True, mode="fixed", self_hosted=False, docs="",
       models=(), profile=CompatProfile()) -> OpenAICompatibleAdapter:
    info = ProviderInfo(id=id_, display_name=name, integration="hosted", requires_api_key=key,
                        suggested_models=list(models), docs_url=docs, category=category,
                        base_url_mode=mode, default_base_url=url, self_hosted=self_hosted)
    return OpenAICompatibleAdapter(info, profile=profile)


def openai_adapter() -> OpenAICompatibleAdapter:
    return _p("openai", "OpenAI", category="frontier", url=None,
              docs="https://platform.openai.com/docs/api-reference/chat",
              profile=CompatProfile(token_param="max_completion_tokens", stream_usage=True))


def xai_adapter() -> OpenAICompatibleAdapter:
    return _p("xai", "xAI Grok", category="frontier", url="https://api.x.ai/v1",
              docs="https://docs.x.ai/docs/api-reference",
              profile=CompatProfile(token_param="max_completion_tokens", stream_usage=True))


def compatible_adapters() -> list[OpenAICompatibleAdapter]:
    """Open-model clouds, routers, and local runtimes that speak the OpenAI API."""
    return [
        _p("huggingface", "Hugging Face", category="open", url="https://router.huggingface.co/v1",
           docs="https://huggingface.co/docs/inference-providers"),
        _p("mistral", "Mistral AI", category="open", url="https://api.mistral.ai/v1",
           docs="https://docs.mistral.ai/api/"),
        _p("groq", "Groq", category="open", url="https://api.groq.com/openai/v1",
           docs="https://console.groq.com/docs/openai"),
        _p("deepseek", "DeepSeek", category="open", url="https://api.deepseek.com",
           docs="https://api-docs.deepseek.com/"),
        _p("together", "Together AI", category="open", url="https://api.together.xyz/v1",
           docs="https://docs.together.ai/docs/openai-api-compatibility"),
        _p("openrouter", "OpenRouter", category="open", url="https://openrouter.ai/api/v1",
           docs="https://openrouter.ai/docs/api-reference/overview"),
        # Ollama documents max_tokens and stream_options.include_usage on /v1/chat/completions.
        # The key is ignored locally; Ollama Cloud (https://ollama.com/v1) needs a real one.
        _p("ollama", "Ollama", category="local", url="http://localhost:11434/v1", key=False, mode="optional",
           self_hosted=True, docs="https://docs.ollama.com/api/openai-compatibility",
           profile=CompatProfile(token_param="max_tokens", stream_usage=True)),
        _p("lmstudio", "LM Studio", category="local", url="http://localhost:1234/v1", key=False, mode="optional",
           self_hosted=True, docs="https://lmstudio.ai/docs/app/api/endpoints/openai"),
        # Not marked self-hosted: it may front a paid API (e.g. a LiteLLM proxy), so usage is costed via
        # PLATO_MODEL_PRICING_JSON or the fallback estimate. User URLs are SSRF-checked regardless.
        _p("openai_compatible", "Custom OpenAI-compatible server", category="custom", url=None, key=False,
           mode="required",
           docs="vLLM, llama.cpp server, LocalAI, TGI, LiteLLM proxy, or any /v1/chat/completions endpoint"),
    ]
