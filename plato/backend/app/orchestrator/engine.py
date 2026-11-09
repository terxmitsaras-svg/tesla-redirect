"""Event-driven multi-agent orchestration engine.

Model
-----
* A **Run** executes a project's agent team against one objective.
* Every agent gets its own asyncio worker and **inbox**. Workers run concurrently; an agent
  only waits on its own inbox, never on another agent.
* An agent turn = drain inbox → stream a completion from its provider → parse directives →
  route messages/tasks into recipients' inboxes. Token deltas stream live to subscribers.
* The run completes on **quiescence** (no agent busy, all inboxes empty, nothing awaiting
  approval) or when a limit trips: turns per agent, agent messages, wall-clock, or USD budget.
* The Commander can message agents, approve/reject delegated tasks, pause/resume, interrupt a
  single agent's generation, or stop the run. Every persisted event is written to the ``events``
  table with a per-run sequence number before it is published, so history survives a refresh.

Scaling note: runs execute inside the API process that started them. The bus can fan out via
Redis, but moving execution to dedicated workers is a Phase 3 item (docs/ARCHITECTURE.md §6).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update

from .. import db
from ..billing_meter import report_platform_usage
from ..core.config import get_settings
from ..core.security import decrypt_secret
from ..models import Agent, Event, Project, ProjectFile, ProviderCredential, Run, Task, UsageRecord, User
from ..plans import get_entitlements
from ..providers.base import ChatMessage, GenerationRequest, ProviderAdapter, ProviderError
from ..providers.registry import get_adapter
from . import protocol as P
from .bus import get_bus
from .pricing import cost_usd
from .prompts import MODES, TeamMember, build_system_prompt, render_inbox_item

log = logging.getLogger("plato.engine")

ACTIVE_STATUSES = {"pending", "running", "paused"}
MAX_RETRIES = 2
MAX_FILE_CHARS = 20_000


class RunError(Exception):
    """Raised for invalid run requests (mapped to HTTP 400 by the API)."""


@dataclass
class Limits:
    max_turns_per_agent: int
    max_agent_messages: int
    max_run_seconds: int
    max_output_tokens: int
    budget_usd: float
    max_concurrent_agents: int

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class InboxItem:
    kind: str  # kickoff | commander | message | task | system
    sender_name: str
    content: str
    title: str = ""
    task_id: str | None = None


@dataclass
class AgentRuntime:
    id: str
    name: str
    role: str
    provider: str
    model: str
    parent_id: str | None
    instructions: str
    adapter: ProviderAdapter
    api_key: str | None
    endpoint: str | None
    billed_to: str  # byok | platform | simulated
    system_prompt: str = ""
    history: list[ChatMessage] = field(default_factory=list)
    inbox: asyncio.Queue[InboxItem] = field(default_factory=asyncio.Queue)
    can_message: set[str] = field(default_factory=set)
    status: str = "idle"
    turns: int = 0
    busy: bool = False
    partial: str = ""
    turn_id: str | None = None
    active_task_ids: list[str] = field(default_factory=list)
    worker: asyncio.Task | None = None
    gen_task: asyncio.Task | None = None
    interrupt_requested: bool = False
    dead: bool = False  # worker crashed; excluded from quiescence
    pending_notes: list[str] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "status": self.status, "turns": self.turns,
                "turn_id": self.turn_id, "partial": self.partial}


class RunRuntime:
    def __init__(self, *, run_id: str, project_id: str, owner_id: str, objective: str, mode: str,
                 limits: Limits, agents: list[AgentRuntime], approve_delegations: bool):
        self.run_id = run_id
        self.project_id = project_id
        self.owner_id = owner_id
        self.objective = objective
        self.mode = mode
        self.limits = limits
        self.agents: dict[str, AgentRuntime] = {a.id: a for a in agents}
        self.approve_delegations = approve_delegations
        self.status = "pending"
        self.seq = 0
        self.agent_messages = 0
        self.cost_usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.awaiting_approval: set[str] = set()
        self.limit_hits: list[str] = []  # soft limits hit by individual agents (e.g. turn limit)
        self.semaphore = asyncio.Semaphore(max(1, limits.max_concurrent_agents))
        self.running_gate = asyncio.Event()
        self.running_gate.set()
        self._emit_lock = asyncio.Lock()
        self._finalizing = False
        self._started = False
        self._watchdog: asyncio.Task | None = None
        self.finished = asyncio.Event()

    # ---------------------------------------------------------------- events
    async def emit(self, type_: str, data: dict[str, Any], *, agent_id: str | None = None) -> dict[str, Any]:
        if type_ in P.EPHEMERAL_TYPES:
            evt = P.envelope(type_, self.project_id, self.run_id, data, agent_id=agent_id)
            await get_bus().publish(evt)
            return evt
        async with self._emit_lock:  # preserves seq order between DB and subscribers
            self.seq += 1
            now = datetime.now(UTC)
            async with db.sessionmaker()() as s:
                s.add(Event(run_id=self.run_id, project_id=self.project_id, seq=self.seq, type=type_,
                            agent_id=agent_id, data=data, created_at=now))
                await s.commit()
            evt = P.envelope(type_, self.project_id, self.run_id, data, agent_id=agent_id, seq=self.seq, ts=now)
            await get_bus().publish(evt)
            return evt

    async def _set_agent_status(self, a: AgentRuntime, status: str) -> None:
        if a.status != status:
            a.status = status
            await self.emit(P.AGENT_STATUS, {"status": status, "name": a.name}, agent_id=a.id)

    async def _set_task(self, task_id: str, status: str, result: str | None = None) -> None:
        async with db.sessionmaker()() as s:
            task = await s.get(Task, task_id)
            if not task:
                return
            task.status = status
            if result is not None:
                task.result = result
            await s.commit()
            data = {"task_id": task.id, "status": status, "title": task.title,
                    "assignee_agent_id": task.assignee_agent_id, "result": task.result}
        await self.emit(P.TASK_UPDATED, data, agent_id=None)

    # ---------------------------------------------------------------- lifecycle
    async def start(self, kickoff: dict[str, str]) -> None:
        self.status = "running"
        await self._persist_run(status="running")
        await self.emit(P.RUN_STATUS, {"status": "running", "objective": self.objective, "mode": self.mode,
                                       "limits": self.limits.as_dict(),
                                       "agents": [{"id": a.id, "name": a.name, "billed_to": a.billed_to}
                                                  for a in self.agents.values()]})
        for a in self.agents.values():
            a.worker = asyncio.create_task(self._agent_loop(a), name=f"agent:{a.name}")
        for agent_id, assignment in kickoff.items():
            a = self.agents[agent_id]
            task_id = await self._create_task(title=f"{a.role or a.name}: contribute to objective",
                                              description=assignment, assignee=a, creator=None, status="pending")
            a.inbox.put_nowait(InboxItem("kickoff", "Commander", assignment, task_id=task_id))
        self._started = True
        self._watchdog = asyncio.create_task(self._watch_clock())

    async def _watch_clock(self) -> None:
        await asyncio.sleep(self.limits.max_run_seconds)
        await self.emit(P.LIMIT_REACHED, {"limit": "max_run_seconds", "value": self.limits.max_run_seconds})
        await self.stop("limit_reached", f"Time limit of {self.limits.max_run_seconds}s reached")

    def _check_quiescent(self) -> None:
        if not self._started or self._finalizing or self.status != "running":
            return
        if self.awaiting_approval:
            return
        for a in self.agents.values():
            if a.dead:
                continue
            if a.busy or not a.inbox.empty():
                return
        if self.limit_hits:
            reason = "Run ended after agents reached limits: " + ", ".join(sorted(set(self.limit_hits)))
            asyncio.create_task(self._finalize("limit_reached", reason))
        else:
            asyncio.create_task(self._finalize("completed", "All agents finished and no messages are pending"))

    async def stop(self, status: str = "stopped", reason: str = "Stopped by Commander") -> None:
        await self._finalize(status, reason)

    async def _finalize(self, status: str, reason: str) -> None:
        if self._finalizing:
            return
        self._finalizing = True
        self.status = status
        self.running_gate.set()  # release paused workers so they can exit
        current = asyncio.current_task()
        # Preserve in-flight output in history before cancelling generations.
        for a in self.agents.values():
            if a.turn_id and a.gen_task and not a.gen_task.done():
                await self.emit(P.TURN_INTERRUPTED, {"turn_id": a.turn_id, "partial": a.partial,
                                                     "reason": reason}, agent_id=a.id)
        for a in self.agents.values():
            for t in (a.gen_task, a.worker):
                if t and t is not current and not t.done():
                    t.cancel()
        workers = [a.worker for a in self.agents.values() if a.worker and a.worker is not current]
        await asyncio.gather(*workers, return_exceptions=True)
        if self._watchdog and self._watchdog is not current:
            self._watchdog.cancel()
        for a in self.agents.values():
            if a.status not in ("error",):
                a.status = "stopped" if status != "completed" else "idle"
        # Close out tasks.
        async with db.sessionmaker()() as s:
            tasks = (await s.scalars(select(Task).where(Task.run_id == self.run_id))).all()
            for t in tasks:
                if t.status in ("pending", "awaiting_approval"):
                    t.status = "cancelled"
                elif t.status == "running":
                    t.status = "unfinished"
            await s.commit()
        await self._persist_run(status=status, stop_reason=reason, ended=True)
        await self.emit(P.RUN_STATUS, {"status": status, "reason": reason, "cost_usd": round(self.cost_usd, 6),
                                       "input_tokens": self.input_tokens, "output_tokens": self.output_tokens})
        self.finished.set()
        get_run_manager().forget(self.run_id)

    async def _persist_run(self, *, status: str, stop_reason: str | None = None, ended: bool = False) -> None:
        values: dict[str, Any] = {"status": status, "cost_usd": self.cost_usd,
                                  "input_tokens": self.input_tokens, "output_tokens": self.output_tokens}
        if stop_reason is not None:
            values["stop_reason"] = stop_reason
        if ended:
            values["ended_at"] = datetime.now(UTC)
        async with db.sessionmaker()() as s:
            await s.execute(update(Run).where(Run.id == self.run_id).values(**values))
            await s.commit()

    async def pause(self) -> None:
        if self.status == "running":
            self.running_gate.clear()
            self.status = "paused"
            await self._persist_run(status="paused")
            await self.emit(P.RUN_STATUS, {"status": "paused", "reason": "Paused by Commander. "
                                           "In-flight replies finish; no new turns start."})

    async def resume(self) -> None:
        if self.status == "paused":
            self.status = "running"
            self.running_gate.set()
            await self._persist_run(status="running")
            await self.emit(P.RUN_STATUS, {"status": "running", "reason": "Resumed by Commander"})
            self._check_quiescent()

    async def interrupt_agent(self, agent_id: str) -> bool:
        a = self.agents.get(agent_id)
        if not a or not a.gen_task or a.gen_task.done():
            return False
        a.interrupt_requested = True
        a.gen_task.cancel()
        return True

    # ---------------------------------------------------------------- commander input
    async def commander_message(self, content: str, to_ids: list[str] | None) -> None:
        if self.status not in ("running", "paused"):
            raise RunError("Run is not active")
        targets = [self.agents[i] for i in (to_ids or []) if i in self.agents] if to_ids else [
            a for a in self.agents.values() if a.parent_id is None]
        if not targets:
            raise RunError("No valid recipients")
        await self.emit(P.MESSAGE_SENT, {"from": "commander", "from_name": "Commander",
                                         "to": [a.id for a in targets], "to_names": [a.name for a in targets],
                                         "content": content, "kind": "commander"})
        for a in targets:
            if not a.dead:
                a.inbox.put_nowait(InboxItem("commander", "Commander", content))

    async def decide_task(self, task_id: str, approve: bool) -> None:
        if task_id not in self.awaiting_approval:
            raise RunError("Task is not awaiting approval")
        self.awaiting_approval.discard(task_id)
        async with db.sessionmaker()() as s:
            task = await s.get(Task, task_id)
            assert task is not None
            assignee, creator_id = task.assignee_agent_id, task.created_by_agent_id
            title, description = task.title, task.description
        creator = self.agents.get(creator_id or "")
        if approve:
            await self._set_task(task_id, "pending")
            a = self.agents[assignee]
            a.inbox.put_nowait(InboxItem("task", creator.name if creator else "Commander", description,
                                         title=title, task_id=task_id))
        else:
            await self._set_task(task_id, "rejected")
            if creator:
                creator.pending_notes.append(f'The Commander rejected your delegated task "{title}".')
        self._check_quiescent()

    # ---------------------------------------------------------------- agent worker
    async def _agent_loop(self, a: AgentRuntime) -> None:
        try:
            while True:
                item = await a.inbox.get()
                items = [item]
                while not a.inbox.empty():
                    items.append(a.inbox.get_nowait())
                a.busy = True
                try:
                    await self.running_gate.wait()
                    if self._finalizing:
                        return
                    if a.turns >= self.limits.max_turns_per_agent:
                        await self._fail_items(items, "turn limit reached")
                        await self.emit(P.LIMIT_REACHED, {"limit": "max_turns_per_agent", "agent": a.name,
                                                          "value": self.limits.max_turns_per_agent}, agent_id=a.id)
                        await self._set_agent_status(a, "limit_reached")
                        self.limit_hits.append(f"{a.name} turn limit ({self.limits.max_turns_per_agent})")
                        continue
                    await self._turn(a, items)
                finally:
                    a.busy = False
                    self._check_quiescent()
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # never let one agent crash the run
            log.exception("agent loop crashed")
            a.status, a.dead = "error", True
            with contextlib.suppress(Exception):
                await self.emit(P.ERROR, {"message": f"{a.name} crashed: {exc}"}, agent_id=a.id)
            self._check_quiescent()

    async def _fail_items(self, items: list[InboxItem], reason: str) -> None:
        for it in items:
            if it.task_id:
                await self._set_task(it.task_id, "failed", reason)

    async def _turn(self, a: AgentRuntime, items: list[InboxItem]) -> None:
        for it in items:
            if it.task_id:
                a.active_task_ids.append(it.task_id)
                await self._set_task(it.task_id, "running")
        rendered = [render_inbox_item(i.kind, i.sender_name, i.content, i.title) for i in items]
        if a.pending_notes:
            rendered += [render_inbox_item("system", "PLATO", n, "") for n in a.pending_notes]
            a.pending_notes.clear()
        a.history.append(ChatMessage("user", "\n\n".join(rendered)))
        a.turns += 1
        a.turn_id = uuid.uuid4().hex
        a.partial = ""
        await self.emit(P.TURN_STARTED, {"turn_id": a.turn_id, "turn": a.turns, "name": a.name,
                                         "inputs": [{"kind": i.kind, "from": i.sender_name} for i in items]},
                        agent_id=a.id)
        await self._set_agent_status(a, "thinking")

        attempt = 0
        while True:
            try:
                async with self.semaphore:
                    await self._set_agent_status(a, "streaming")
                    a.interrupt_requested = False
                    a.gen_task = asyncio.create_task(self._generate(a))
                    text, usage = await a.gen_task
                break
            except asyncio.CancelledError:
                if not a.interrupt_requested or self._finalizing:
                    raise
                text = a.partial
                a.history.append(ChatMessage("assistant", (text or "") + "\n[interrupted by the Commander]"))
                await self.emit(P.TURN_INTERRUPTED, {"turn_id": a.turn_id, "partial": text}, agent_id=a.id)
                await self._set_agent_status(a, "idle")
                a.turn_id, a.partial = None, ""
                return
            except ProviderError as exc:
                if exc.retryable and attempt < MAX_RETRIES:
                    attempt += 1
                    await self.emit(P.ERROR, {"message": f"{exc} Retrying ({attempt}/{MAX_RETRIES})…",
                                              "retrying": True}, agent_id=a.id)
                    await asyncio.sleep(1.5 * 2 ** (attempt - 1))
                    a.partial = ""
                    continue
                await self.emit(P.ERROR, {"message": str(exc), "retrying": False}, agent_id=a.id)
                a.history.pop()  # the failed user turn can be re-sent later
                for tid in a.active_task_ids:
                    await self._set_task(tid, "failed", str(exc))
                a.active_task_ids.clear()
                await self._set_agent_status(a, "error")
                a.turn_id, a.partial = None, ""
                return
            finally:
                a.gen_task = None

        await self._record_usage(a, usage)
        parsed = P.parse_reply(text)
        a.history.append(ChatMessage("assistant", text))
        await self.emit(P.TURN_COMPLETED, {
            "turn_id": a.turn_id, "name": a.name, "text": text, "visible_text": parsed.visible_text,
            "usage": usage, "done": parsed.done,
        }, agent_id=a.id)
        a.turn_id, a.partial = None, ""

        for d in parsed.directives:
            if self._finalizing:
                break
            await self._route(a, d)
        if parsed.done is not None:
            for tid in a.active_task_ids:
                await self._set_task(tid, "completed", parsed.done)
            a.active_task_ids.clear()
            await self._set_agent_status(a, "done")
        else:
            await self._set_agent_status(a, "idle")

        if self.cost_usd >= self.limits.budget_usd and not self._finalizing:
            await self.emit(P.LIMIT_REACHED, {"limit": "budget_usd", "value": self.limits.budget_usd})
            asyncio.create_task(self.stop("limit_reached", f"Budget of ${self.limits.budget_usd:.2f} reached"))

    async def _generate(self, a: AgentRuntime) -> tuple[str, dict[str, Any]]:
        req = GenerationRequest(model=a.model, system=a.system_prompt, messages=list(a.history),
                                max_output_tokens=self.limits.max_output_tokens)
        chunks: list[str] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        async for ev in a.adapter.stream(req, api_key=a.api_key, endpoint=a.endpoint):
            if ev.type == "text":
                chunks.append(ev.text)
                a.partial += ev.text
                await self.emit(P.TURN_DELTA, {"turn_id": a.turn_id, "text": ev.text}, agent_id=a.id)
            elif ev.type == "usage":
                usage = {"input_tokens": ev.input_tokens, "output_tokens": ev.output_tokens,
                         "stop_reason": ev.stop_reason, "tokens_estimated": ev.estimated}
        return "".join(chunks), usage

    async def _record_usage(self, a: AgentRuntime, usage: dict[str, Any]) -> None:
        if a.billed_to in ("simulated", "self_hosted"):
            cost, known = 0.0, True  # no per-token API charge (runs offline / on the user's hardware)
        else:
            cost, known = cost_usd(a.provider, a.model, usage["input_tokens"], usage["output_tokens"])
        usage["cost_usd"] = round(cost, 6)
        usage["cost_is_estimate"] = a.billed_to not in ("simulated", "self_hosted")  # invoices are authoritative
        usage["price_known"] = known
        self.cost_usd += cost
        self.input_tokens += usage["input_tokens"]
        self.output_tokens += usage["output_tokens"]
        async with db.sessionmaker()() as s:
            s.add(UsageRecord(owner_id=self.owner_id, run_id=self.run_id, agent_id=a.id, provider=a.provider,
                              model=a.model, input_tokens=usage["input_tokens"],
                              output_tokens=usage["output_tokens"], cost_usd=cost,
                              cost_is_estimate=not known or bool(usage.get("tokens_estimated")),
                              billed_to=a.billed_to))
            if a.billed_to == "platform":
                user = await s.get(User, self.owner_id)
                if user:
                    user.credits_usd = max(0.0, user.credits_usd - cost)
                    asyncio.create_task(report_platform_usage(user.stripe_customer_id, cost))
                    if user.credits_usd <= 0 and not self._finalizing:
                        asyncio.create_task(self.stop("limit_reached", "Platform usage credits exhausted"))
            await s.commit()
        await self._persist_run(status=self.status)
        await self.emit(P.USAGE, {"cost_usd": round(self.cost_usd, 6), "input_tokens": self.input_tokens,
                                  "output_tokens": self.output_tokens, "budget_usd": self.limits.budget_usd})

    # ---------------------------------------------------------------- routing
    def _resolve(self, names: list[str], sender: AgentRuntime) -> tuple[list[AgentRuntime], list[str]]:
        by_name = {a.name.lower(): a for a in self.agents.values()}
        found: list[AgentRuntime] = []
        unknown: list[str] = []
        for n in names:
            if n.lower() == "all":
                found += [a for a in self.agents.values() if a.id != sender.id and a.id in sender.can_message]
                continue
            a = by_name.get(n.lower())
            if a is None or a.id == sender.id:
                unknown.append(n)
            elif a not in found:
                found.append(a)
        return found, unknown

    async def _reject(self, a: AgentRuntime, reason: str) -> None:
        a.pending_notes.append(reason)
        await self.emit(P.DIRECTIVE_REJECTED, {"reason": reason, "name": a.name}, agent_id=a.id)

    async def _route(self, sender: AgentRuntime, d: P.Directive) -> None:
        targets, unknown = self._resolve(d.to, sender)
        if unknown:
            await self._reject(sender, f"Unknown recipient(s): {', '.join(unknown)}")
        allowed = [t for t in targets if t.id in sender.can_message]
        denied = [t for t in targets if t.id not in sender.can_message]
        if denied:
            await self._reject(sender, f"Not permitted to contact {', '.join(t.name for t in denied)} "
                                       f"in {MODES[self.mode]['label']} mode")
        if not allowed or not d.content:
            return

        self.agent_messages += 1
        if self.agent_messages > self.limits.max_agent_messages:
            await self.emit(P.LIMIT_REACHED, {"limit": "max_agent_messages", "value": self.limits.max_agent_messages})
            asyncio.create_task(self.stop("limit_reached",
                                          f"Agent message limit of {self.limits.max_agent_messages} reached"))
            return

        if d.kind == "message":
            await self.emit(P.MESSAGE_SENT, {"from": sender.id, "from_name": sender.name,
                                             "to": [t.id for t in allowed], "to_names": [t.name for t in allowed],
                                             "content": d.content, "kind": "message"}, agent_id=sender.id)
            for t in allowed:
                if not t.dead:
                    t.inbox.put_nowait(InboxItem("message", sender.name, d.content))
        else:  # task: single assignee
            t = allowed[0]
            status = "awaiting_approval" if self.approve_delegations else "pending"
            task_id = await self._create_task(title=d.title or f"Task from {sender.name}", description=d.content,
                                              assignee=t, creator=sender, status=status)
            if status == "pending":
                t.inbox.put_nowait(InboxItem("task", sender.name, d.content, title=d.title, task_id=task_id))
            else:
                self.awaiting_approval.add(task_id)

    async def _create_task(self, *, title: str, description: str, assignee: AgentRuntime,
                           creator: AgentRuntime | None, status: str) -> str:
        async with db.sessionmaker()() as s:
            task = Task(owner_id=self.owner_id, project_id=self.project_id, run_id=self.run_id, title=title[:200],
                        description=description, assignee_agent_id=assignee.id,
                        created_by_agent_id=creator.id if creator else None, status=status)
            s.add(task)
            await s.commit()
            task_id = task.id
        await self.emit(P.TASK_CREATED, {"task_id": task_id, "title": title, "description": description,
                                         "assignee_agent_id": assignee.id, "assignee_name": assignee.name,
                                         "created_by": creator.name if creator else "Commander",
                                         "status": status}, agent_id=creator.id if creator else None)
        return task_id

    def snapshot(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "status": self.status, "seq": self.seq, "cost_usd": round(self.cost_usd, 6),
                "agents": [a.public() for a in self.agents.values()],
                "awaiting_approval": sorted(self.awaiting_approval)}


# ====================================================================== manager
def _permissions(policy: str, me: TeamMember, team: list[TeamMember]) -> set[str]:
    others = [m for m in team if m.id != me.id]
    if policy == "isolated":
        return set()
    if policy == "hierarchical":
        out = set()
        for m in others:
            if m.parent_id == me.id or me.parent_id == m.id or (m.parent_id is None and me.parent_id is None):
                out.add(m.id)
        return out
    return {m.id for m in others}


class RunManager:
    def __init__(self) -> None:
        self.runs: dict[str, RunRuntime] = {}

    def get(self, run_id: str) -> RunRuntime | None:
        return self.runs.get(run_id)

    def forget(self, run_id: str) -> None:
        self.runs.pop(run_id, None)

    def active_for_project(self, project_id: str) -> list[RunRuntime]:
        return [r for r in self.runs.values() if r.project_id == project_id]

    async def start_run(self, *, user: User, project: Project, objective: str, mode: str | None,
                        overrides: dict[str, Any], assignments: dict[str, str]) -> Run:
        settings = get_settings()
        objective = objective.strip()
        if not objective:
            raise RunError("Objective is required")
        mode = mode or project.settings.get("mode") or "open_discussion"
        if mode not in MODES:
            raise RunError(f"Unknown collaboration mode: {mode}")

        async with db.sessionmaker()() as s:
            ent = await get_entitlements(s, user)
            active = [r for r in self.runs.values() if r.owner_id == user.id]
            if len(active) >= (ent.get("max_parallel_runs") or 1):
                raise RunError(f"Your plan allows {ent.get('max_parallel_runs')} simultaneous run(s)")
            agents = (await s.scalars(select(Agent).where(Agent.project_id == project.id,
                                                          Agent.owner_id == user.id,
                                                          Agent.is_active.is_(True)))).all()
            if not agents:
                raise RunError("Add at least one agent to this project first")
            files = (await s.scalars(select(ProjectFile).where(ProjectFile.project_id == project.id,
                                                               ProjectFile.shared_with_agents.is_(True)))).all()
            creds = {c.id: c for c in (await s.scalars(
                select(ProviderCredential).where(ProviderCredential.owner_id == user.id))).all()}
            fresh_user = await s.get(User, user.id)
            credits = fresh_user.credits_usd if fresh_user else 0.0

            def clamp(key: str, default: float, cap_key: str | None = None) -> float:
                v = overrides.get(key, project.settings.get(key, default))
                cap = ent.get(cap_key or key)
                return min(v, cap) if cap is not None else v

            limits = Limits(
                max_turns_per_agent=int(clamp("max_turns_per_agent", settings.default_max_turns_per_agent)),
                max_agent_messages=int(clamp("max_agent_messages", settings.default_max_agent_messages)),
                max_run_seconds=int(clamp("max_run_seconds", settings.default_max_run_seconds)),
                max_output_tokens=int(min(overrides.get("max_output_tokens", project.settings.get(
                    "max_output_tokens", settings.default_max_output_tokens)), 32_000)),
                budget_usd=float(overrides.get("budget_usd", project.settings.get(
                    "budget_usd", settings.default_run_budget_usd))),
                max_concurrent_agents=int(ent.get("max_concurrent_agents") or 2),
            )

            team = [TeamMember(a.id, a.name, a.role, a.provider, a.model, a.parent_id) for a in agents]
            policy = MODES[mode]["policy"]
            runtimes: list[AgentRuntime] = []
            for a, member in zip(agents, team, strict=True):
                adapter = get_adapter(a.provider)
                api_key: str | None = None
                endpoint = a.external_url
                billed = "byok"
                if adapter.info.integration == "simulated":
                    billed = "simulated"
                elif a.kind == "external" or adapter.info.integration == "external":
                    cred = creds.get(a.credential_id or "")
                    api_key = decrypt_secret(cred.encrypted_key) if cred else None
                else:
                    cred = creds.get(a.credential_id or "") or next(
                        (c for c in creds.values() if c.provider == a.provider), None)
                    if cred:
                        api_key = decrypt_secret(cred.encrypted_key) or None
                        endpoint = cred.base_url
                    elif not adapter.info.requires_api_key:
                        pass  # keyless runtime on its default URL (e.g. local Ollama)
                    elif settings.platform_key(a.provider) and credits > 0:
                        api_key, billed = settings.platform_key(a.provider), "platform"
                    else:
                        raise RunError(f"Agent '{a.name}' has no {adapter.info.display_name} API key. "
                                       f"Connect the provider first.")
                    if adapter.info.self_hosted:
                        billed = "self_hosted"
                can_message = _permissions(policy, member, team)
                file_ctx = [(f.path, f.content[:MAX_FILE_CHARS]) for f in files]
                rt = AgentRuntime(
                    id=a.id, name=a.name, role=a.role, provider=a.provider, model=a.model, parent_id=a.parent_id,
                    instructions=a.instructions, adapter=adapter, api_key=api_key, endpoint=endpoint,
                    billed_to=billed, can_message=can_message,
                )
                rt.system_prompt = build_system_prompt(
                    me=member, team=team, instructions=a.instructions, mode=mode, objective=objective,
                    shared_context=project.shared_context, files=file_ctx, can_message=can_message)
                runtimes.append(rt)

            primaries = [r for r in runtimes if r.parent_id is None]
            kickoff: dict[str, str] = {}
            for r in primaries:
                kickoff[r.id] = assignments.get(r.id) or objective
            for agent_id, text in assignments.items():  # explicit assignments may target subagents too
                if agent_id in {r.id for r in runtimes}:
                    kickoff[agent_id] = text

            run = Run(owner_id=user.id, project_id=project.id, objective=objective, mode=mode,
                      status="pending", limits=limits.as_dict())
            s.add(run)
            await s.commit()
            await s.refresh(run)

        rt_run = RunRuntime(run_id=run.id, project_id=project.id, owner_id=user.id, objective=objective, mode=mode,
                            limits=limits, agents=runtimes,
                            approve_delegations=bool(project.settings.get("approve_delegations", False)))
        self.runs[run.id] = rt_run
        await rt_run.start(kickoff)
        run.status = "running"
        return run

    async def shutdown(self) -> None:
        for r in list(self.runs.values()):
            await r.stop("interrupted", "Server shutting down")


_manager: RunManager | None = None


def get_run_manager() -> RunManager:
    global _manager
    if _manager is None:
        _manager = RunManager()
    return _manager


async def recover_orphaned_runs() -> int:
    """Runs can't survive a process restart (agent state is in memory); mark them interrupted."""
    async with db.sessionmaker()() as s:
        res = await s.execute(update(Run).where(Run.status.in_(ACTIVE_STATUSES)).values(
            status="interrupted", stop_reason="Server restarted while the run was active",
            ended_at=datetime.now(UTC)))
        await s.commit()
        return res.rowcount or 0
