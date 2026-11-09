"""A local HTTP server that speaks each provider's real streaming wire format.

Used to verify that PLATO's adapters (which use the official SDKs) parse genuine SSE payloads.
This is a test double: it is NOT used at runtime.
"""
from __future__ import annotations

import json
import socket
import threading
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
BAD_KEY = "bad-key-000000"
CAPTURED: dict[str, dict] = {}


def _sse(events: list[tuple[str | None, dict | str]]):
    async def gen():
        for name, data in events:
            if name:
                yield f"event: {name}\n"
            yield f"data: {data if isinstance(data, str) else json.dumps(data)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


def _auth_failed(request: Request, header: str) -> bool:
    # SDKs may send the key in a provider header or as a bearer token; check both.
    v = request.headers.get(header, "") + request.headers.get("authorization", "")
    return BAD_KEY in v


# ---------------- Anthropic
@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    if _auth_failed(request, "x-api-key"):
        return JSONResponse({"type": "error", "error": {"type": "authentication_error", "message": "bad key"}},
                            status_code=401)
    body = await request.json()
    CAPTURED["anthropic"] = {"body": body, "query": str(request.url.query),
                             "beta": request.headers.get("anthropic-beta")}
    msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"], "content": [],
           "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 42, "output_tokens": 1}}
    return _sse([
        ("message_start", {"type": "message_start", "message": msg}),
        ("content_block_start", {"type": "content_block_start", "index": 0,
                                 "content_block": {"type": "text", "text": ""}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                 "delta": {"type": "text_delta", "text": "Hello "}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                 "delta": {"type": "text_delta", "text": "from Claude"}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                           "usage": {"output_tokens": 7}}),
        ("message_stop", {"type": "message_stop"}),
    ])


@app.get("/v1/models")
async def anthropic_models(request: Request):
    if _auth_failed(request, "x-api-key"):
        return JSONResponse({"type": "error", "error": {"type": "authentication_error", "message": "bad"}},
                            status_code=401)
    return {"data": [{"type": "model", "id": "claude-opus-5-5", "display_name": "Claude Opus 5.5",
                      "created_at": "2026-01-01T00:00:00Z"}],
            "has_more": False, "first_id": "claude-opus-5-5", "last_id": "claude-opus-5-5"}


# ---------------- OpenAI-compatible (OpenAI, xAI)
@app.post("/openai/v1/chat/completions")
async def openai_chat(request: Request):
    if _auth_failed(request, "authorization"):
        return JSONResponse({"error": {"message": "bad key", "type": "invalid_request_error"}}, status_code=401)
    body = await request.json()
    CAPTURED["openai"] = {"body": body}
    base = {"id": "c1", "object": "chat.completion.chunk", "created": 0, "model": body["model"]}
    return _sse([
        (None, {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}]}),
        (None, {**base, "choices": [{"index": 0, "delta": {"content": "Hi "}}]}),
        (None, {**base, "choices": [{"index": 0, "delta": {"content": "from GPT"}, "finish_reason": "stop"}]}),
        (None, {**base, "choices": [], "usage": {"prompt_tokens": 30, "completion_tokens": 5, "total_tokens": 35}}),
        (None, "[DONE]"),
    ])


@app.get("/openai/v1/models")
async def openai_models(request: Request):
    if _auth_failed(request, "authorization"):
        return JSONResponse({"error": {"message": "bad key"}}, status_code=401)
    return {"object": "list", "data": [{"id": "model-b", "object": "model", "created": 0, "owned_by": "x"},
                                       {"id": "model-a", "object": "model", "created": 0, "owned_by": "x"}]}


# ---------------- Other OpenAI-compatible servers
# "strict": like many compatible servers — rejects OpenAI-only params and reports no usage.
# "ollama": documents max_tokens + stream_options.include_usage.
# "groq":   reports usage in a non-standard x_groq.usage field.
@app.post("/compat/{flavor}/v1/chat/completions")
async def compat_chat(flavor: str, request: Request):
    body = await request.json()
    CAPTURED[flavor] = {"body": body, "auth": request.headers.get("authorization")}
    if flavor not in ("strict", "ollama", "groq"):
        return JSONResponse({"error": {"message": "unknown"}}, status_code=404)
    if "max_completion_tokens" in body:
        return JSONResponse({"error": {"message": "unknown field max_completion_tokens"}}, status_code=400)
    if flavor != "ollama" and "stream_options" in body:
        return JSONResponse({"error": {"message": "unknown field stream_options"}}, status_code=400)
    base = {"id": "c1", "object": "chat.completion.chunk", "created": 0, "model": body["model"]}
    events: list = [
        (None, {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Local "}}]}),
        (None, {**base, "choices": [{"index": 0, "delta": {"content": "model reply"}, "finish_reason": "stop"}]}),
    ]
    if flavor == "ollama":
        events.append((None, {**base, "choices": [], "usage": {"prompt_tokens": 11, "completion_tokens": 3,
                                                              "total_tokens": 14}}))
    if flavor == "groq":
        events[-1][1]["x_groq"] = {"id": "req_1", "usage": {"prompt_tokens": 9, "completion_tokens": 2}}
    events.append((None, "[DONE]"))
    return _sse(events)


@app.get("/compat/{flavor}/v1/models")
async def compat_models(flavor: str):
    return {"object": "list", "data": [{"id": "llama3.2", "object": "model", "created": 0, "owned_by": "library"}]}


# ---------------- Gemini
@app.post("/gemini/{version}/models/{model_action}")
async def gemini_stream(version: str, model_action: str, request: Request):
    if _auth_failed(request, "x-goog-api-key"):
        return JSONResponse({"error": {"code": 401, "message": "bad key", "status": "UNAUTHENTICATED"}},
                            status_code=401)
    body = await request.json()
    CAPTURED["gemini"] = {"body": body, "path": model_action}

    def chunk(text, final=False):
        c = {"content": {"parts": [{"text": text}], "role": "model"}, "index": 0}
        out = {"candidates": [c]}
        if final:
            c["finishReason"] = "STOP"
            out["usageMetadata"] = {"promptTokenCount": 20, "candidatesTokenCount": 4, "totalTokenCount": 24}
        return out

    return _sse([(None, chunk("Hey ")), (None, chunk("from Gemini", final=True))])


@app.get("/gemini/{version}/models")
async def gemini_models(version: str, request: Request):
    return {"models": [{"name": "models/gemini-x", "supportedGenerationMethods": ["generateContent"]},
                       {"name": "models/embed-x", "supportedGenerationMethods": ["embedContent"]}]}


class FakeProviderServer:
    def __init__(self) -> None:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started:
            if time.time() > deadline:
                raise RuntimeError("fake provider server did not start")
            time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=5)
