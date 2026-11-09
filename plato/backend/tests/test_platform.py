"""Auth, tenancy isolation, plan entitlements, credentials (BYOK), hosted provider runs, billing."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time

import pytest

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.providers.anthropic_adapter import AnthropicAdapter
from app.providers.openai_adapter import OpenAICompatibleAdapter, openai_adapter
from app.providers.registry import register_adapter

from .conftest import add_agent, make_project, register, wait_run_done
from .fake_providers import BAD_KEY, FakeProviderServer
from .test_orchestration import set_plan


# ------------------------------------------------------------------ auth
def test_auth_flow(client):
    h = register(client, "Mixed@Case.dev")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["email"] == "mixed@case.dev" and me["plan_code"] == "free"
    assert client.post("/api/auth/register", json={"email": "mixed@case.dev", "password": "x" * 12}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "mixed@case.dev", "password": "wrong-pass-123"}).status_code \
        == 401
    assert client.post("/api/auth/login", json={"email": "MIXED@case.dev",
                                                 "password": "correct-horse-battery"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/auth/register", json={"email": "short@x.dev", "password": "short"}).status_code == 422


def test_login_rate_limited(client):
    register(client, "rl@x.dev")
    codes = [client.post("/api/auth/login", json={"email": "rl@x.dev", "password": "bad-password-1"}).status_code
             for _ in range(12)]
    assert 429 in codes


def test_ws_requires_valid_single_use_ticket(client):
    h = register(client)
    pid = make_project(client, h)
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/projects/{pid}?ticket=forged") as ws:
        ws.receive_json()
    ticket = client.post("/api/auth/ws-ticket", headers=h).json()["ticket"]
    with client.websocket_connect(f"/ws/projects/{pid}?ticket={ticket}") as ws:
        assert ws.receive_json()["type"] == "snapshot"
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/projects/{pid}?ticket={ticket}") as ws:
        ws.receive_json()  # replayed ticket is rejected


# ------------------------------------------------------------------ tenancy
def test_tenant_isolation(client):
    ha = register(client, "alice@x.dev")
    hb = register(client, "bob@x.dev")
    pid = make_project(client, ha)
    agent = add_agent(client, ha, pid, "Secret")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=ha, json={"objective": "x"}).json()["id"]
    wait_run_done(client, ha, run_id)

    for path in (f"/api/projects/{pid}", f"/api/projects/{pid}/agents", f"/api/projects/{pid}/files",
                 f"/api/runs/{run_id}", f"/api/runs/{run_id}/events", f"/api/projects/{pid}/tasks"):
        assert client.get(path, headers=hb).status_code == 404, path
    assert client.patch(f"/api/agents/{agent['id']}", headers=hb, json={"role": "pwned"}).status_code == 404
    assert client.delete(f"/api/projects/{pid}", headers=hb).status_code == 404
    assert client.get("/api/projects", headers=hb).json() == []
    # Bob cannot open Alice's live stream either.
    from starlette.websockets import WebSocketDisconnect

    t = client.post("/api/auth/ws-ticket", headers=hb).json()["ticket"]
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/projects/{pid}?ticket={t}") as ws:
        ws.receive_json()


# ------------------------------------------------------------------ plans
def test_free_plan_entitlements(client, tmp_path):
    h = register(client)
    pid = make_project(client, h)
    assert client.post("/api/projects", headers=h, json={"name": "Second"}).status_code == 402
    a = add_agent(client, h, pid, "One", model="sim-fast")
    add_agent(client, h, pid, "Two", model="sim-slow")
    add_agent(client, h, pid, "Three", expect=402)  # max 2 configured agents

    set_plan(tmp_path, "pro")
    add_agent(client, h, pid, "Sub", parent_id=a["id"])  # hierarchies on Pro
    sub = client.get(f"/api/projects/{pid}/agents", headers=h).json()[-1]
    r = client.post(f"/api/projects/{pid}/agents", headers=h, json={
        "name": "Deep", "provider": "mock", "model": "sim-fast", "parent_id": sub["id"]})
    assert r.status_code == 400 and "max depth" in r.json()["detail"]


def test_model_limit_counts_distinct_models(client, tmp_path):
    register_adapter(_paid("p1"))
    h = register(client)
    pid = make_project(client, h)
    add_agent(client, h, pid, "M1", model="sim-fast")
    add_agent(client, h, pid, "M2", model="sim-slow")
    set_plan(tmp_path, "pro")  # 8 agents, 4 models
    for i, m in enumerate(["m3", "m4"]):
        add_agent(client, h, pid, f"X{i}", provider="p1", model=m)
    r = client.post(f"/api/projects/{pid}/agents", headers=h,
                    json={"name": "X9", "provider": "p1", "model": "m5"})
    assert r.status_code == 402 and "distinct AI model" in r.json()["detail"]
    add_agent(client, h, pid, "Reuse", provider="p1", model="m3")  # an existing model is fine


def _paid(pid):
    from .test_orchestration import ScriptedAdapter

    return ScriptedAdapter(lambda *a: "<done>x</done>", pid=pid)


def test_agent_name_rules(client):
    h = register(client)
    pid = make_project(client, h)
    for bad in ("all", "Commander", "<script>"):
        r = client.post(f"/api/projects/{pid}/agents", headers=h,
                        json={"name": bad, "provider": "mock", "model": "sim-fast"})
        assert r.status_code == 422, bad
    add_agent(client, h, pid, "Dup")
    add_agent(client, h, pid, "dup", expect=409)


# ------------------------------------------------------------------ credentials + hosted run (real SDK path)
@pytest.fixture
def fake_upstream():
    with FakeProviderServer() as srv:
        yield srv


def test_byok_credentials_are_verified_encrypted_and_hidden(client, fake_upstream, tmp_path):
    register_adapter(AnthropicAdapter(base_url=fake_upstream.url))
    h = register(client)
    r = client.post("/api/credentials", headers=h, json={"provider": "anthropic", "api_key": BAD_KEY})
    assert r.status_code == 400 and "verification failed" in r.json()["detail"]

    secret = "sk-ant-test-abcdef123456"
    r = client.post("/api/credentials", headers=h, json={"provider": "anthropic", "api_key": secret})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["key_hint"] == "…3456" and body["verified_at"] and secret not in json.dumps(body)
    assert secret not in json.dumps(client.get("/api/credentials", headers=h).json())

    con = sqlite3.connect(tmp_path / "plato-test.db")
    stored = con.execute("select encrypted_key from provider_credentials").fetchone()[0]
    con.close()
    assert secret not in stored and decrypt_secret(stored) == secret

    models = client.get("/api/providers/anthropic/models", headers=h).json()
    assert models == {"models": ["claude-opus-5-5"], "live": True}
    providers = {p["id"]: p for p in client.get("/api/providers", headers=h).json()}
    assert providers["anthropic"]["connected"] and not providers["openai"]["connected"]
    assert providers["mock"]["integration"] == "simulated"


def test_hosted_claude_and_openai_agents_run_through_real_sdks(client, fake_upstream):
    """Same pipeline as production: BYOK key decrypted → official SDK → HTTP streaming → events."""
    register_adapter(AnthropicAdapter(base_url=fake_upstream.url))
    register_adapter(OpenAICompatibleAdapter(openai_adapter().info, base_url=fake_upstream.url + "/openai/v1"))
    h = register(client)
    for prov in ("anthropic", "openai"):
        assert client.post("/api/credentials", headers=h,
                           json={"provider": prov, "api_key": f"sk-{prov}-good-key-1"}).status_code == 201
    pid = make_project(client, h)
    a = add_agent(client, h, pid, "Claude", provider="anthropic", model="claude-opus-5-5")
    b = add_agent(client, h, pid, "GPT", provider="openai", model="model-a")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "hello"}).json()["id"]
    run = wait_run_done(client, h, run_id)
    assert run["status"] == "completed"
    ev = client.get(f"/api/runs/{run_id}/events", headers=h).json()
    texts = {e["agent_id"]: e["data"]["text"] for e in ev if e["type"] == "agent.turn.completed"}
    assert texts == {a["id"]: "Hello from Claude", b["id"]: "Hi from GPT"}
    assert run["input_tokens"] == 42 + 30 and run["output_tokens"] == 7 + 5
    # Claude Opus 5.5 is $4/$20 per MTok (known price); the unknown OpenAI model uses the fallback estimate.
    expected = (42 * 4 + 7 * 20) / 1e6 + (30 * 5 + 5 * 20) / 1e6
    assert run["cost_usd"] == pytest.approx(expected)
    summary = client.get("/api/billing/summary", headers=h).json()
    assert {m["billed_to"] for m in summary["usage_by_model"]} == {"byok"}


def test_platform_managed_key_consumes_credits(client, fake_upstream, monkeypatch):
    register_adapter(AnthropicAdapter(base_url=fake_upstream.url))
    monkeypatch.setattr(get_settings(), "platform_anthropic_key", "sk-platform-good-key")
    h = register(client)
    before = client.get("/api/auth/me", headers=h).json()["credits_usd"]
    pid = make_project(client, h)
    add_agent(client, h, pid, "Claude", provider="anthropic", model="claude-sonnet-5-5")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"}).json()["id"]
    assert wait_run_done(client, h, run_id)["status"] == "completed"
    after = client.get("/api/auth/me", headers=h).json()["credits_usd"]
    assert after == pytest.approx(before - (42 * 2 + 7 * 10) / 1e6)


# ------------------------------------------------------------------ billing
def _sign(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_stripe_webhooks_change_plan(client, monkeypatch, tmp_path):
    secret = "whsec_test_secret"
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", secret)
    h = register(client)
    uid = client.get("/api/auth/me", headers=h).json()["id"]

    def send(evt: dict, sig: str | None = None):
        payload = json.dumps(evt).encode()
        return client.post("/api/billing/webhook", content=payload,
                           headers={"stripe-signature": sig or _sign(payload, secret),
                                    "content-type": "application/json"})

    evt = {"id": "evt_1", "object": "event", "type": "checkout.session.completed", "data": {"object": {
        "id": "cs_1", "object": "checkout.session", "customer": "cus_1", "subscription": "sub_1",
        "client_reference_id": uid, "metadata": {"plato_user_id": uid, "plan_code": "power"}}}}
    assert send(evt, sig="t=1,v1=deadbeef").status_code == 400  # forged signature
    assert send(evt).status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["plan_code"] == "power"

    con = sqlite3.connect(tmp_path / "plato-test.db")
    con.execute("update plans set stripe_price_id='price_pro' where code='pro'")
    con.commit()
    con.close()
    upd = {"id": "evt_2", "object": "event", "type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_1", "object": "subscription", "customer": "cus_1", "status": "active",
        "items": {"data": [{"price": {"id": "price_pro"}}]}}}}
    assert send(upd).status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["plan_code"] == "pro"

    paid = {"id": "evt_3", "object": "event", "type": "invoice.paid", "data": {"object": {"customer": "cus_1"}}}
    send(paid)
    assert client.get("/api/auth/me", headers=h).json()["credits_usd"] == pytest.approx(5.0)

    gone = {"id": "evt_4", "object": "event", "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_1", "customer": "cus_1"}}}
    send(gone)
    assert client.get("/api/auth/me", headers=h).json()["plan_code"] == "free"


def test_checkout_requires_stripe_configuration(client):
    h = register(client)
    assert client.post("/api/billing/checkout", headers=h, json={"plan_code": "pro"}).status_code == 503
    plans = client.get("/api/billing/plans").json()
    assert [(p["code"], p["price_usd_month"]) for p in plans] == [
        ("free", 0.0), ("pro", 19.0), ("power", 49.0), ("business", 149.0)]


def test_admin_can_edit_plan_prices(client, tmp_path):
    h = register(client, "admin@plato.dev")
    assert client.patch("/api/admin/plans/pro", headers=h, json={"price_usd_month": 25}).status_code == 403
    con = sqlite3.connect(tmp_path / "plato-test.db")
    con.execute("update users set is_admin=1")
    con.commit()
    con.close()
    r = client.patch("/api/admin/plans/pro", headers=h,
                     json={"price_usd_month": 25, "entitlements": {"max_agents": 10}})
    assert r.status_code == 200
    assert r.json()["price_usd_month"] == 25 and r.json()["entitlements"]["max_agents"] == 10
    assert r.json()["entitlements"]["max_models"] == 4  # merged, not replaced
    logs = client.get("/api/audit-logs", headers=h).json()
    assert any(entry["action"] == "admin.plan.update" for entry in logs)
