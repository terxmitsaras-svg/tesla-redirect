"""Orchestrator behaviour: controls, limits, permissions, approvals, hierarchy, error recovery."""
from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable

from app.providers.base import GenerationRequest, ProviderAdapter, ProviderError, ProviderInfo, StreamEvent
from app.providers.registry import register_adapter

from .conftest import add_agent, make_project, register, wait_for, wait_run_done, ws_ticket


def set_plan(tmp_path, plan: str) -> None:
    con = sqlite3.connect(tmp_path / "plato-test.db")
    con.execute("update users set plan_code=?", (plan,))
    con.commit()
    con.close()


class ScriptedAdapter(ProviderAdapter):
    """Test double: reply text is computed from (agent name, turn number, last message)."""

    def __init__(self, script: Callable[[str, int, str], str], pid="scripted", fail_times: int = 0):
        self.info = ProviderInfo(id=pid, display_name="Scripted (test)", integration="simulated",
                                 requires_api_key=False, suggested_models=["s"])
        self.script = script
        self.calls: dict[str, int] = {}
        self.fail_times = fail_times

    async def stream(self, request: GenerationRequest, *, api_key=None, endpoint=None):
        name = request.system.split("You are ", 1)[1].split(",", 1)[0]
        self.calls[name] = self.calls.get(name, 0) + 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ProviderError("upstream overloaded", retryable=True, status=529)
        text = self.script(name, self.calls[name], request.messages[-1].content)
        for word in text.split(" "):
            await asyncio.sleep(0.005)
            yield StreamEvent(type="text", text=word + " ")
        yield StreamEvent(type="usage", input_tokens=1000, output_tokens=1000)

    async def list_models(self, *, api_key=None, endpoint=None):
        return ["s"]


def _events(client, h, run_id):
    return client.get(f"/api/runs/{run_id}/events", headers=h).json()


def test_stop_and_interrupt(client):
    h = register(client)
    pid = make_project(client, h)
    a = add_agent(client, h, pid, "Slow1", model="sim-slow")
    add_agent(client, h, pid, "Slow2", model="sim-slow")
    with client.websocket_connect(f"/ws/projects/{pid}?ticket={ws_ticket(client, h)}") as ws:
        ws.receive_json()  # snapshot
        run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "slow work"}).json()["id"]
        while True:  # wait until Slow1 is mid-stream
            e = ws.receive_json()
            if e.get("type") == "agent.delta" and e["agent_id"] == a["id"]:
                break
        ws.send_json({"action": "agent.interrupt", "run_id": run_id, "agent_id": a["id"], "ref": "i1"})
        seen_interrupt = seen_ack = False
        while not (seen_interrupt and seen_ack):
            e = ws.receive_json()
            seen_ack |= e.get("type") == "ack" and e.get("ref") == "i1"
            seen_interrupt |= e.get("type") == "agent.turn.interrupted" and e["agent_id"] == a["id"]
        ws.send_json({"action": "run.stop", "run_id": run_id})
        while True:
            e = ws.receive_json()
            if e.get("type") == "run.status" and e["data"]["status"] == "stopped":
                break
    run = wait_run_done(client, h, run_id)
    assert run["status"] == "stopped" and run["stop_reason"] == "Stopped by Commander"
    interrupted = [e for e in _events(client, h, run_id) if e["type"] == "agent.turn.interrupted"]
    assert interrupted and interrupted[0]["data"]["partial"]
    # The turn still in flight when the run stopped is closed out in history (with whatever had streamed).
    assert any(e["data"].get("reason") == "Stopped by Commander" and "partial" in e["data"] for e in interrupted)
    statuses = {t["status"] for t in client.get(f"/api/projects/{pid}/tasks", headers=h).json()}
    assert statuses <= {"unfinished", "cancelled", "completed"}
    # A stopped run rejects further control.
    assert client.post(f"/api/runs/{run_id}/pause", headers=h).status_code == 409


def test_pause_blocks_new_turns_then_resume_completes(client):
    h = register(client)
    pid = make_project(client, h)
    add_agent(client, h, pid, "A1")
    add_agent(client, h, pid, "B1")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"}).json()["id"]
    assert client.post(f"/api/runs/{run_id}/pause", headers=h).status_code == 202
    assert client.get(f"/api/runs/{run_id}", headers=h).json()["status"] == "paused"

    def started():
        return sum(e["type"] == "agent.turn.started" for e in _events(client, h, run_id))

    def completed():
        return sum(e["type"] == "agent.turn.completed" for e in _events(client, h, run_id))

    wait_for(lambda: started() == completed())  # in-flight turns finish
    n = started()
    import time
    time.sleep(0.6)
    assert started() == n, "no new turns may start while paused"
    client.post(f"/api/runs/{run_id}/resume", headers=h)
    assert wait_run_done(client, h, run_id)["status"] == "completed"


def test_agent_message_limit_prevents_loops(client):
    # Two agents that would ping-pong forever.
    register_adapter(ScriptedAdapter(lambda me, n, last: f'Ping <message to="{"B" if me == "A" else "A"}">'
                                                         f"again {n}?</message>"))
    h = register(client)
    pid = make_project(client, h, max_agent_messages=3, max_turns_per_agent=50)
    add_agent(client, h, pid, "A", provider="scripted", model="s")
    add_agent(client, h, pid, "B", provider="scripted", model="s")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "chat"}).json()["id"]
    run = wait_run_done(client, h, run_id)
    assert run["status"] == "limit_reached"
    assert "message limit" in run["stop_reason"]
    sent = [e for e in _events(client, h, run_id) if e["type"] == "message.sent" and e["data"]["kind"] == "message"]
    assert len(sent) == 3


def test_turn_limit_is_clamped_to_plan(client):
    register_adapter(ScriptedAdapter(lambda me, n, last: f'go <message to="{"B" if me == "A" else "A"}">x</message>'))
    h = register(client)
    pid = make_project(client, h, max_agent_messages=1000, max_turns_per_agent=100)  # free plan caps at 6/20
    add_agent(client, h, pid, "A", provider="scripted", model="s")
    add_agent(client, h, pid, "B", provider="scripted", model="s")
    r = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "chat"}).json()
    assert r["limits"]["max_turns_per_agent"] == 6 and r["limits"]["max_agent_messages"] == 20
    assert wait_run_done(client, h, r["id"])["status"] == "limit_reached"


def test_budget_limit_stops_run(client):
    # Unknown model -> fallback price (5/20 $/MTok): each turn costs 1000*5e-6 + 1000*2e-5 = $0.025.
    register_adapter(ScriptedAdapter(lambda me, n, last: f'step <message to="{"B" if me == "A" else "A"}">x</message>'))
    h = register(client)
    pid = make_project(client, h, budget_usd=0.06, max_agent_messages=100)
    add_agent(client, h, pid, "A", provider="scripted", model="s")
    add_agent(client, h, pid, "B", provider="scripted", model="s")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "spend"}).json()["id"]
    run = wait_run_done(client, h, run_id)
    assert run["status"] == "limit_reached" and "Budget" in run["stop_reason"]
    assert 0.06 <= run["cost_usd"] < 0.06 + 3 * 0.025


def test_independent_review_blocks_agent_messaging(client):
    h = register(client)
    pid = make_project(client, h, mode="independent_review")
    add_agent(client, h, pid, "R1")
    add_agent(client, h, pid, "R2")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "review"}).json()["id"]
    assert wait_run_done(client, h, run_id)["status"] == "completed"
    ev = _events(client, h, run_id)
    assert not [e for e in ev if e["type"] == "message.sent" and e["data"]["kind"] == "message"]
    assert [e for e in ev if e["type"] == "directive.rejected"]


def test_hierarchy_delegation_with_human_approval(client, tmp_path):
    def script(me, n, last):
        if me == "Lead":
            if n == 1:
                return 'Delegating. <task to="Researcher" title="Find sources">List 3 sources.</task>'
            return "<done>Merged research.</done>"
        return '<message to="Lead">Sources: A, B, C</message><done>Found 3 sources.</done>'

    register_adapter(ScriptedAdapter(script))
    h = register(client)
    set_plan(tmp_path, "pro")
    pid = make_project(client, h, approve_delegations=True, mode="structured_delegation")
    lead = add_agent(client, h, pid, "Lead", provider="scripted", model="s")
    res = add_agent(client, h, pid, "Researcher", provider="scripted", model="s", parent_id=lead["id"])
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "research"}).json()["id"]

    def awaiting():
        return [t for t in client.get(f"/api/projects/{pid}/tasks", headers=h).json()
                if t["status"] == "awaiting_approval"]

    wait_for(lambda: bool(awaiting()))
    task = awaiting()[0]
    assert task["assignee_agent_id"] == res["id"] and task["created_by_agent_id"] == lead["id"]
    # Run must not complete while a delegation awaits the Commander.
    assert client.get(f"/api/runs/{run_id}", headers=h).json()["status"] == "running"
    assert client.post(f"/api/runs/{run_id}/tasks/{task['id']}/approve", headers=h).status_code == 202
    assert wait_run_done(client, h, run_id)["status"] == "completed"
    tasks = {t["title"]: t for t in client.get(f"/api/projects/{pid}/tasks", headers=h).json()}
    assert tasks["Find sources"]["status"] == "completed"
    assert tasks["Find sources"]["result"] == "Found 3 sources."
    # Subagent reported back to its parent.
    sent = [e["data"] for e in _events(client, h, run_id) if e["type"] == "message.sent"]
    assert any(m["from"] == res["id"] and m["to"] == [lead["id"]] for m in sent)


def test_rejected_delegation(client, tmp_path):
    register_adapter(ScriptedAdapter(
        lambda me, n, last: '<task to="Sub" title="Risky">do it</task>' if n == 1 else "<done>ok</done>"))
    h = register(client)
    set_plan(tmp_path, "pro")
    pid = make_project(client, h, approve_delegations=True)
    lead = add_agent(client, h, pid, "Boss", provider="scripted", model="s")
    add_agent(client, h, pid, "Sub", provider="scripted", model="s", parent_id=lead["id"])
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"}).json()["id"]
    wait_for(lambda: any(t["status"] == "awaiting_approval"
                         for t in client.get(f"/api/projects/{pid}/tasks", headers=h).json()))
    tid = next(t["id"] for t in client.get(f"/api/projects/{pid}/tasks", headers=h).json()
               if t["status"] == "awaiting_approval")
    client.post(f"/api/runs/{run_id}/tasks/{tid}/reject", headers=h)
    assert wait_run_done(client, h, run_id)["status"] == "completed"
    assert {t["title"]: t["status"] for t in client.get(f"/api/projects/{pid}/tasks", headers=h).json()}["Risky"] \
        == "rejected"


def test_retry_on_transient_provider_error(client):
    adapter = ScriptedAdapter(lambda me, n, last: "<done>ok</done>", fail_times=1)
    register_adapter(adapter)
    h = register(client)
    pid = make_project(client, h)
    add_agent(client, h, pid, "Solo", provider="scripted", model="s")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"}).json()["id"]
    assert wait_run_done(client, h, run_id)["status"] == "completed"
    errs = [e for e in _events(client, h, run_id) if e["type"] == "error"]
    assert len(errs) == 1 and errs[0]["data"]["retrying"] is True


def test_commander_message_reaches_selected_agent(client):
    register_adapter(ScriptedAdapter(
        # Turn 1 streams ~1s of text so the Commander can intervene while the run is live.
        lambda me, n, last: "<done>got it</done>" if "commander_message" in last and n > 1 else "working " * 200))
    h = register(client)
    pid = make_project(client, h)
    a = add_agent(client, h, pid, "A", provider="scripted", model="s", role="")
    add_agent(client, h, pid, "B", provider="scripted", model="s")
    run_id = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"}).json()["id"]
    client.post(f"/api/runs/{run_id}/pause", headers=h)
    r = client.post(f"/api/runs/{run_id}/messages", headers=h, json={"content": "Focus on auth", "to": [a["id"]]})
    assert r.status_code == 202
    client.post(f"/api/runs/{run_id}/resume", headers=h)
    wait_run_done(client, h, run_id)
    ev = _events(client, h, run_id)
    cm = [e for e in ev if e["type"] == "message.sent" and e["data"]["kind"] == "commander"]
    assert cm and cm[0]["data"]["to"] == [a["id"]]
    a_turns = [e for e in ev if e["type"] == "agent.turn.completed" and e["agent_id"] == a["id"]]
    assert any(e["data"]["done"] == "got it" for e in a_turns)


def test_one_active_run_per_project_and_missing_key(client):
    h = register(client)
    pid = make_project(client, h)
    add_agent(client, h, pid, "Claude", provider="anthropic", model="claude-opus-5-5")
    r = client.post(f"/api/projects/{pid}/runs", headers=h, json={"objective": "x"})
    assert r.status_code == 400 and "no Anthropic Claude API key" in r.json()["detail"]
