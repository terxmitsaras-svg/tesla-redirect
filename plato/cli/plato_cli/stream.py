"""Live run viewer over the PLATO WebSocket."""
from __future__ import annotations

import asyncio
import json
import re
import sys
from collections.abc import Callable
from typing import Any

from websockets.asyncio.client import connect

from . import term
from .client import Client

FINAL = {"completed", "stopped", "limit_reached", "interrupted", "failed"}

# Complete directives are removed; an unfinished directive (or a "<" that might start one) at the end
# of the buffer is held back until we know. The visible text therefore only ever grows, so it can be
# printed incrementally without retracting anything.
_COMPLETE = re.compile(r"<(message|task)\b[^>]*>.*?</\1>|<done>.*?</done>", re.DOTALL | re.IGNORECASE)
_OPEN_TAIL = re.compile(r"<(message|task|done)\b.*$", re.DOTALL | re.IGNORECASE)
_PARTIAL_TAIL = re.compile(r"<(m(e(s(s(a(g(e)?)?)?)?)?)?|t(a(s(k)?)?)?|d(o(n(e)?)?)?)?$", re.IGNORECASE)


def visible(text: str) -> str:
    text = _COMPLETE.sub("", text)
    text = _OPEN_TAIL.sub("", text)
    return _PARTIAL_TAIL.sub("", text)


class Renderer:
    """Turns the event stream into a readable transcript.

    Several agents stream at the same time, but a terminal has one cursor. In live mode the renderer
    follows ONE speaker at a time: other agents' tokens are buffered and their replies printed in full
    when the current speaker finishes. Lines caused by a buffered reply (its handoffs, "done") are held
    back and printed right after that reply, so the transcript always reads in a sensible order.
    """

    def __init__(self, agents: dict[str, dict], live: bool, out: Callable[[str], None] | None = None):
        self.agents = agents
        self.live = live
        self.out = out or (lambda s: (sys.stdout.write(s), sys.stdout.flush()))
        self.colors = {aid: term.AGENT_PALETTE[i % len(term.AGENT_PALETTE)] for i, aid in enumerate(agents)}
        # turn_id -> {agent, text, printed, final (str when the turn is over), after: [lines]}
        self.turns: dict[str, dict[str, Any]] = {}
        self.order: list[str] = []  # turns not yet fully shown, in the order they started
        self.speaker: str | None = None
        self.at_line_start = True
        self.needs_label = False

    # ------------------------------------------------------------------ output primitives
    def name(self, agent_id: str | None) -> str:
        return self.agents.get(agent_id or "", {}).get("name", "Agent")

    def label(self, agent_id: str | None) -> str:
        return term.c(f"[{self.name(agent_id)}]", self.colors.get(agent_id or "", "white"), bold=True)

    def _write(self, s: str) -> None:
        if s:
            self.out(s)
            self.at_line_start = s.endswith("\n")

    def _line(self, s: str) -> None:
        if not self.at_line_start:
            self._write("\n")
        self._write(s + "\n")
        if self.speaker:
            self.needs_label = True  # the live speaker resumes on a fresh, labelled line

    # ------------------------------------------------------------------ turn bookkeeping
    def _turn(self, turn_id: str, agent_id: str | None) -> dict[str, Any]:
        if turn_id not in self.turns:
            self.turns[turn_id] = {"agent": agent_id, "text": "", "printed": 0, "final": None, "after": []}
            self.order.append(turn_id)
        return self.turns[turn_id]

    def _print_speaker(self) -> None:
        turn = self.turns[self.speaker]  # type: ignore[index]
        vis = turn["final"] if turn["final"] is not None else visible(turn["text"])
        new = vis[turn["printed"]:]
        if not new:
            return
        if turn["printed"] == 0 or self.needs_label:
            if not self.at_line_start:
                self._write("\n")
            self._write(f"{self.label(turn['agent'])} ")
            if turn["printed"] == 0:
                new = new.lstrip()
            self.needs_label = False
        self._write(new)
        turn["printed"] = len(vis)

    def _finish_speaker(self) -> None:
        tid = self.speaker
        assert tid is not None
        self._print_speaker()
        turn = self.turns.pop(tid)
        self.order.remove(tid)
        self.speaker, self.needs_label = None, False
        if not self.at_line_start:
            self._write("\n")
        for line in turn["after"]:
            self._write(line + "\n")

    def _advance(self) -> None:
        """Pick the next speaker; replies that already finished are printed whole."""
        while self.speaker is None and self.order:
            self.speaker = self.order[0]
            if self.turns[self.speaker]["final"] is not None:
                self._finish_speaker()
            else:
                self._print_speaker()

    def _end_turn(self, turn_id: str, agent_id: str | None, raw_text: str, after: list[str]) -> None:
        turn = self._turn(turn_id, agent_id)
        turn["final"] = visible(raw_text).rstrip()
        turn["after"] = after + turn["after"]
        if self.speaker == turn_id:
            self._finish_speaker()
        self._advance()

    def _buffered_turn_of(self, agent_id: str | None) -> dict[str, Any] | None:
        """A finished-but-not-yet-shown reply by this agent (its follow-up lines must wait for it)."""
        for tid in reversed(self.order):
            t = self.turns[tid]
            if t["agent"] == agent_id and t["final"] is not None and tid != self.speaker:
                return t
        return None

    def _emit(self, line: str, agent_id: str | None) -> None:
        owner = self._buffered_turn_of(agent_id) if (self.live and agent_id) else None
        if owner is not None:
            owner["after"].append(line)
        else:
            self._line(line)

    def flush(self) -> None:
        for tid in self.order:
            t = self.turns[tid]
            if t["final"] is None:
                t["final"] = visible(t["text"]).rstrip()
        if self.speaker:
            self._finish_speaker()
        self._advance()

    # ------------------------------------------------------------------ events
    def handle(self, e: dict[str, Any]) -> str | None:
        """Render one event; return the final run status when the run ends."""
        t, d, aid = e.get("type"), e.get("data") or {}, e.get("agent_id")
        if t == "agent.turn.started" and self.live:
            self._turn(d["turn_id"], aid)
        elif t == "agent.delta":
            if not self.live:
                return None
            self._turn(d["turn_id"], aid)["text"] += d.get("text", "")
            if self.speaker is None:
                self._advance()
            elif self.speaker == d["turn_id"]:
                self._print_speaker()
        elif t == "agent.turn.completed":
            done = [term.c(f"  ✓ {self.name(aid)} done: {d['done']}", "green")] if d.get("done") else []
            if self.live:
                self._end_turn(d["turn_id"], aid, d.get("text") or "", done)
            else:
                text = (d.get("visible_text") or "").strip()
                if text:
                    self._line(f"{self.label(aid)} {text}")
                for line in done:
                    self._line(line)
        elif t == "agent.turn.interrupted":
            note = [term.c(f"  ⏸ {self.name(aid)} interrupted", "yellow")]
            if self.live:
                self._end_turn(d["turn_id"], aid, d.get("partial") or "", note)
            else:
                self._line(note[0])
        elif t == "message.sent":
            to = ", ".join(d.get("to_names") or [])
            if d.get("kind") == "commander":
                self._line(term.c(f"› You → {to}: ", "blue", bold=True) + d.get("content", ""))
            else:
                self._emit(term.c(f"  ✉ {d.get('from_name')} → {to}: ", "magenta") + d.get("content", ""), aid)
        elif t == "task.created":
            note = " (awaiting your approval: plato approve)" if d.get("status") == "awaiting_approval" else ""
            self._emit(term.c(f"  + task “{d.get('title')}” {d.get('created_by')} → {d.get('assignee_name')}{note}",
                              "grey"), aid)
        elif t == "task.updated" and d.get("status") in ("completed", "failed", "rejected"):
            color = "green" if d["status"] == "completed" else "red"
            self._line(term.c(f"  • task “{d.get('title')}” {d['status']}", color))
        elif t in ("limit.reached", "directive.rejected"):
            msg = d.get("reason") or f"limit {d.get('limit')} = {d.get('value')}"
            self._emit(term.c(f"  ! {msg}", "yellow"), aid)
        elif t == "error":
            self._emit(term.c(f"  ! {self.name(aid)}: {d.get('message')}", "yellow" if d.get("retrying") else "red"),
                       aid)
        elif t == "run.status":
            status = d.get("status")
            if status == "running" and not d.get("reason"):
                self._line(term.c(f"▶ Run started · mode {d.get('mode', '')}", "cyan", bold=True))
            elif status in FINAL:
                self.flush()
                cost = d.get("cost_usd")
                extra = f" · est. ${cost:.4f}" if isinstance(cost, int | float) else ""
                summary = f"■ Run {status.replace('_', ' ')} — {d.get('reason', '')}{extra}"
                self._line(term.c(summary, "cyan", bold=True))
                return status
            else:
                self._line(term.c(f"• Run {status}{' — ' + d['reason'] if d.get('reason') else ''}", "grey"))
        return None


async def watch(client: Client, project_id: str, *, start: dict | None = None, run_id: str | None = None,
                live: bool = True, as_json: bool = False) -> tuple[str, str | None]:
    """Stream a run. With ``start`` the run is created *after* the socket is open so nothing is missed.
    Returns (final_status, run_id)."""
    cfg = client.cfg
    ticket = (await asyncio.to_thread(client.post, "/api/auth/ws-ticket"))["ticket"]
    agents = {a["id"]: a for a in await asyncio.to_thread(client.get, f"/api/projects/{project_id}/agents")}
    renderer = Renderer(agents, live=live)
    ws_url = cfg.server.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    async with connect(f"{ws_url}/ws/projects/{project_id}?ticket={ticket}", max_size=2**22) as ws:
        json.loads(await ws.recv())  # snapshot
        if start is not None:
            run = await asyncio.to_thread(client.post, f"/api/projects/{project_id}/runs", start)
            run_id = run["id"]
            if not as_json:
                renderer._line(term.c(f"Run {run_id} · objective: {run['objective']}", "grey"))
        else:
            # Attaching to a run in progress: replay what already happened.
            for e in await asyncio.to_thread(client.get, f"/api/runs/{run_id}/events"):
                e.setdefault("run_id", run_id)
                if as_json:
                    print(json.dumps(e), flush=True)
                else:
                    status = renderer.handle(e)
                    if status:
                        return status, run_id
        async for raw in ws:
            e = json.loads(raw)
            if e.get("run_id") != run_id:
                continue
            if as_json:
                print(json.dumps(e), flush=True)
                if e["type"] == "run.status" and e["data"].get("status") in FINAL:
                    return e["data"]["status"], run_id
                continue
            status = renderer.handle(e)
            if status:
                return status, run_id
    run = await asyncio.to_thread(client.get, f"/api/runs/{run_id}")
    return run["status"], run_id
