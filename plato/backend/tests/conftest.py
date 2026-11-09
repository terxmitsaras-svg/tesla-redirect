from __future__ import annotations

import os
import time
from collections.abc import Callable

os.environ.setdefault("PLATO_ENV", "test")
os.environ.setdefault("PLATO_ENABLE_MOCK_PROVIDER", "true")
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost,testserver"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.core import ratelimit  # noqa: E402
from app.orchestrator import bus as bus_mod  # noqa: E402
from app.orchestrator import engine as engine_mod  # noqa: E402
from app.providers import registry as reg  # noqa: E402


@pytest.fixture
def client(tmp_path):
    db.init_engine(f"sqlite+aiosqlite:///{tmp_path}/plato-test.db")
    bus_mod._bus = None
    engine_mod._manager = None
    reg._REGISTRY.clear()
    for lim in (ratelimit.auth_limiter, ratelimit.run_limiter, ratelimit.ws_message_limiter):
        lim.reset()
    from app.main import app

    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str = "commander@plato.dev") -> dict[str, str]:
    r = client.post("/api/auth/register", json={"email": email, "password": "correct-horse-battery", "name": "Cmdr"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def make_project(client: TestClient, h: dict, **settings) -> str:
    r = client.post("/api/projects", headers=h, json={"name": "Demo", "settings": settings})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_agent(client: TestClient, h: dict, pid: str, name: str, *, provider="mock", model="sim-fast",
              role="", parent_id=None, expect=201) -> dict:
    r = client.post(f"/api/projects/{pid}/agents", headers=h, json={
        "name": name, "role": role or f"{name} role", "provider": provider, "model": model,
        "parent_id": parent_id, "instructions": "Be concise."})
    assert r.status_code == expect, r.text
    return r.json()


def wait_for(fn: Callable[[], bool], timeout: float = 20.0, interval: float = 0.05) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if fn():
            return
        time.sleep(interval)
    raise AssertionError("condition not met in time")


def wait_run_done(client: TestClient, h: dict, run_id: str, timeout: float = 20.0) -> dict:
    out: dict = {}

    def done() -> bool:
        out.update(client.get(f"/api/runs/{run_id}", headers=h).json())
        return out["status"] not in ("pending", "running", "paused")

    wait_for(done, timeout)
    return out


def ws_ticket(client: TestClient, h: dict) -> str:
    return client.post("/api/auth/ws-ticket", headers=h).json()["ticket"]
