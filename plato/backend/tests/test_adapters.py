"""Wire-level adapter tests: official SDKs → real HTTP → fake upstream speaking each provider's format."""
from __future__ import annotations

import os

import pytest

from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.base import ChatMessage, GenerationRequest, ProviderError
from app.providers.gemini_adapter import GeminiAdapter
from app.providers.openai_adapter import OpenAICompatibleAdapter, openai_adapter

from .fake_providers import BAD_KEY, CAPTURED, FakeProviderServer

# The SDKs honour proxy env vars; the fake server is local.
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"


@pytest.fixture(scope="module")
def fake():
    with FakeProviderServer() as srv:
        yield srv


REQ = GenerationRequest(model="test-model", system="You are a test.", max_output_tokens=256,
                        messages=[ChatMessage("user", "hi"), ChatMessage("user", "again"),
                                  ChatMessage("assistant", "ok"), ChatMessage("user", "go")])


async def _collect(adapter, req=REQ, key="good-key-123456"):
    text, usage = "", None
    async for ev in adapter.stream(req, api_key=key):
        if ev.type == "text":
            text += ev.text
        else:
            usage = ev
    return text, usage


async def test_anthropic_streaming(fake):
    text, usage = await _collect(AnthropicAdapter(base_url=fake.url))
    assert text == "Hello from Claude"
    assert (usage.input_tokens, usage.output_tokens, usage.stop_reason) == (42, 7, "end_turn")
    body = CAPTURED["anthropic"]["body"]
    assert body["system"] == "You are a test." and body["stream"] is True
    # consecutive user turns are merged so roles alternate
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    assert CAPTURED["anthropic"]["beta"] is None


async def test_anthropic_uses_refusal_fallback_on_supported_models(fake):
    req = GenerationRequest(model="claude-opus-5-5", system="s", messages=[ChatMessage("user", "x")])
    text, _ = await _collect(AnthropicAdapter(base_url=fake.url), req)
    assert text == "Hello from Claude"
    assert "server-side-fallback-2026-07-01" in (CAPTURED["anthropic"]["beta"] or "")
    assert CAPTURED["anthropic"]["body"]["fallbacks"] == "default"


async def test_anthropic_list_models_and_bad_key(fake):
    a = AnthropicAdapter(base_url=fake.url)
    assert await a.list_models(api_key="good-key-123456") == ["claude-opus-5-5"]
    with pytest.raises(ProviderError, match="rejected the API key"):
        await a.list_models(api_key=BAD_KEY)


async def test_openai_streaming_and_models(fake):
    a = OpenAICompatibleAdapter(openai_adapter().info, base_url=fake.url + "/openai/v1")
    text, usage = await _collect(a)
    assert text == "Hi from GPT"
    assert (usage.input_tokens, usage.output_tokens, usage.stop_reason) == (30, 5, "stop")
    body = CAPTURED["openai"]["body"]
    assert body["messages"][0] == {"role": "system", "content": "You are a test."}
    assert body["stream_options"] == {"include_usage": True}
    assert await a.list_models(api_key="good-key-123456") == ["model-a", "model-b"]
    with pytest.raises(ProviderError, match="rejected the API key"):
        await _collect(a, key=BAD_KEY)


async def test_gemini_streaming_and_models(fake):
    a = GeminiAdapter(base_url=fake.url + "/gemini/")
    text, usage = await _collect(a)
    assert text == "Hey from Gemini"
    assert (usage.input_tokens, usage.output_tokens) == (20, 4)
    cap = CAPTURED["gemini"]
    assert cap["path"] == "test-model:streamGenerateContent"
    assert [c["role"] for c in cap["body"]["contents"]] == ["user", "model", "user"]
    assert "You are a test." in str(cap["body"].get("systemInstruction") or cap["body"].get("system_instruction"))
    assert await a.list_models(api_key="good-key-123456") == ["gemini-x"]
    with pytest.raises(ProviderError):
        await _collect(a, key=BAD_KEY)
