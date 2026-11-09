"""Connected external agent runtimes.

Unlike hosted agents (PLATO calls a provider's model API), an *external* agent is a runtime the
user operates — e.g. a local coding agent or an SDK-based agent service — that implements the
small **PLATO External Agent Protocol v1** (see docs/PROTOCOL.md §4):

    POST <endpoint>                 Content-Type: application/json
    {"protocol": "plato.agent.v1", "model": str, "system": str,
     "messages": [{"role": "user"|"assistant", "content": str}], "max_output_tokens": int}

    -> 200 text/event-stream
    data: {"type": "text", "text": "..."}
    data: {"type": "usage", "input_tokens": 12, "output_tokens": 34}
    data: {"type": "error", "message": "..."}
    data: [DONE]

PLATO never exposes credentials or files to the runtime beyond what is in the request.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from ..core.netguard import UnsafeURLError, validate_endpoint_url
from .base import GenerationRequest, ProviderAdapter, ProviderError, ProviderInfo, StreamEvent, merge_consecutive


async def validate_external_url(url: str) -> None:
    try:
        await validate_endpoint_url(url)
    except UnsafeURLError as exc:
        raise ProviderError(f"External agent URL rejected: {exc}") from exc


class ExternalAgentAdapter(ProviderAdapter):
    info = ProviderInfo(
        id="external", display_name="Connected external agent", integration="external",
        requires_api_key=False, suggested_models=["default"], category="custom", base_url_mode="required",
        docs_url="docs/PROTOCOL.md#4-external-agent-protocol",
    )

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport  # injectable for tests

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport, timeout=httpx.Timeout(300.0, connect=10.0))

    async def stream(
        self, request: GenerationRequest, *, api_key: str | None, endpoint: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        if not endpoint:
            raise ProviderError("External agent has no endpoint URL.")
        await validate_external_url(endpoint)
        headers = {"Accept": "text/event-stream"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "protocol": "plato.agent.v1",
            "model": request.model,
            "system": request.system,
            "messages": [{"role": m.role, "content": m.content} for m in merge_consecutive(request.messages)],
            "max_output_tokens": request.max_output_tokens,
        }
        usage = StreamEvent(type="usage")
        try:
            async with self._client() as client, client.stream("POST", endpoint, json=body, headers=headers) as resp:
                if resp.status_code >= 400:
                    raise ProviderError(f"External agent returned HTTP {resp.status_code}",
                                        retryable=resp.status_code >= 500, status=resp.status_code)
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        evt = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    kind = evt.get("type")
                    if kind == "text" and evt.get("text"):
                        yield StreamEvent(type="text", text=str(evt["text"]))
                    elif kind == "usage":
                        usage = StreamEvent(type="usage", input_tokens=int(evt.get("input_tokens", 0)),
                                            output_tokens=int(evt.get("output_tokens", 0)))
                    elif kind == "error":
                        raise ProviderError(f"External agent error: {evt.get('message', 'unknown')}")
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach external agent: {exc}", retryable=True) from exc
        yield usage

    async def list_models(self, *, api_key: str | None, endpoint: str | None = None) -> list[str]:
        if not endpoint:
            raise ProviderError("External agent has no endpoint URL.")
        await validate_external_url(endpoint)
        return ["default"]
