"""The mandatory demonstration (§10), executed end-to-end through the real API, WebSocket,
orchestrator and database — with the SIMULATED provider standing in for live models.

The same path with real provider SDKs is covered in test_hosted_run.py (fake upstream) and can
be run against live APIs with scripts/live_demo.py.
"""
from __future__ import annotations

from .conftest import add_agent, make_project, register, wait_run_done, ws_ticket


def test_two_agents_collaborate_live_and_history_survives_refresh(client):
    h = register(client)
    pid = make_project(client, h)
    a = add_agent(client, h, pid, "Architect", role="Software architect")
    b = add_agent(client, h, pid, "Developer", role="Lead developer")

    events: list[dict] = []
    with client.websocket_connect(f"/ws/projects/{pid}?ticket={ws_ticket(client, h)}") as ws:
        snap = ws.receive_json()
        assert snap["type"] == "snapshot" and snap["data"]["active_runs"] == []

        r = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "Design a URL shortener"})
        assert r.status_code == 201, r.text
        run_id = r.json()["id"]

        while True:
            evt = ws.receive_json()
            if evt.get("type") in ("ack", "error"):
                continue
            events.append(evt)
            if evt["type"] == "run.status" and evt["data"]["status"] not in ("running", "paused"):
                break

    types = [e["type"] for e in events]
    assert events[-1]["data"]["status"] == "completed", events[-1]

    # Both agents streamed token deltas live.
    delta_agents = {e["agent_id"] for e in events if e["type"] == "agent.delta"}
    assert delta_agents == {a["id"], b["id"]}

    # Concurrency: both agents started their first turn before either finished one.
    first_done = types.index("agent.turn.completed")
    started_before = {e["agent_id"] for e in events[:first_done] if e["type"] == "agent.turn.started"}
    assert started_before == {a["id"], b["id"]}

    # Agent A → Agent B, and Agent B → Agent A (direct agent-to-agent messaging, no copy/paste).
    msgs = [e["data"] for e in events if e["type"] == "message.sent" and e["data"]["kind"] == "message"]
    assert any(m["from"] == a["id"] and m["to"] == [b["id"]] for m in msgs)
    assert any(m["from"] == b["id"] and m["to"] == [a["id"]] for m in msgs)
    # B's reply to A's question arrives after A's question was delivered.
    a_to_b = next(i for i, m in enumerate(msgs) if m["from"] == a["id"])
    assert any(m["from"] == b["id"] and "Here is my part" in m["content"] for m in msgs[a_to_b:])

    # Persisted events carry a gap-free per-run sequence; deltas are ephemeral (seq None).
    persisted = [e for e in events if e["seq"] is not None]
    assert [e["seq"] for e in persisted] == list(range(1, len(persisted) + 1))
    assert all(e["seq"] is None for e in events if e["type"] == "agent.delta")

    # "Refresh the page": history is fully available over REST.
    hist = client.get(f"/api/runs/{run_id}/events", headers=h).json()
    assert [e["seq"] for e in hist] == [e["seq"] for e in persisted]
    assert "agent.delta" not in {e["type"] for e in hist}
    completed = [e for e in hist if e["type"] == "agent.turn.completed"]
    assert completed and all(e["data"]["text"] for e in completed)
    run = wait_run_done(client, h, run_id)
    assert run["status"] == "completed" and run["ended_at"]

    tasks = client.get(f"/api/projects/{pid}/tasks", headers=h).json()
    assert len(tasks) == 2 and {t["status"] for t in tasks} == {"completed"}

    # Usage was metered and labelled simulated.
    summary = client.get("/api/billing/summary", headers=h).json()
    assert summary["usage_by_model"][0]["billed_to"] == "simulated"
    assert summary["total_cost_usd"] == 0


def test_incremental_history_after_seq(client):
    h = register(client)
    pid = make_project(client, h)
    add_agent(client, h, pid, "Solo")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"}).json()["id"]
    wait_run_done(client, h, run_id)
    hist = client.get(f"/api/runs/{run_id}/events", headers=h).json()
    tail = client.get(f"/api/runs/{run_id}/events?after_seq=3", headers=h).json()
    assert [e["seq"] for e in tail] == [e["seq"] for e in hist if e["seq"] > 3]
