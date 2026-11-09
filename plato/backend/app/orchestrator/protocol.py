"""Real-time event protocol + the agent directive language.

Server → client events share one envelope (see docs/PROTOCOL.md):

    {"type": str, "project_id": str, "run_id": str | None, "agent_id": str | None,
     "seq": int | None, "ts": ISO-8601, "data": {...}}

``seq`` is set on persisted events (monotonic per run) and is ``None`` on ephemeral events
(token deltas), which are never stored.

Agents act on the team by embedding *directives* in their replies. Directives are plain XML-ish
tags so they work identically across every provider (no provider-specific tool calling needed):

    <message to="Name[, Name…]|all">text</message>   send a message
    <task to="Name" title="Short title">details</task>  delegate a task
    <done>summary</done>                             finish current assignment
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---- event types -----------------------------------------------------------------------------
RUN_STATUS = "run.status"
AGENT_STATUS = "agent.status"
TURN_STARTED = "agent.turn.started"
TURN_DELTA = "agent.delta"  # ephemeral
TURN_COMPLETED = "agent.turn.completed"
TURN_INTERRUPTED = "agent.turn.interrupted"
MESSAGE_SENT = "message.sent"
TASK_CREATED = "task.created"
TASK_UPDATED = "task.updated"
USAGE = "usage.updated"
LIMIT_REACHED = "limit.reached"
DIRECTIVE_REJECTED = "directive.rejected"
ERROR = "error"
SNAPSHOT = "snapshot"  # sent once on websocket connect

EPHEMERAL_TYPES = {TURN_DELTA}


def envelope(
    type_: str, project_id: str, run_id: str | None, data: dict[str, Any], *,
    agent_id: str | None = None, seq: int | None = None, ts: datetime | None = None,
) -> dict[str, Any]:
    return {
        "type": type_, "project_id": project_id, "run_id": run_id, "agent_id": agent_id,
        "seq": seq, "ts": (ts or datetime.now(UTC)).isoformat(), "data": data,
    }


# ---- directives --------------------------------------------------------------------------------
MAX_DIRECTIVE_CHARS = 8000

_MESSAGE_RE = re.compile(r'<message\s+to\s*=\s*"([^"]{1,300})"\s*>(.*?)</message>', re.DOTALL | re.IGNORECASE)
_TASK_RE = re.compile(
    r'<task\s+to\s*=\s*"([^"]{1,100})"(?:\s+title\s*=\s*"([^"]{0,200})")?\s*>(.*?)</task>', re.DOTALL | re.IGNORECASE
)
_DONE_RE = re.compile(r"<done>(.*?)</done>", re.DOTALL | re.IGNORECASE)
_ANY_DIRECTIVE_RE = re.compile(r"<(message|task)\b[^>]*>.*?</\1>|<done>.*?</done>", re.DOTALL | re.IGNORECASE)


@dataclass
class Directive:
    kind: str  # "message" | "task"
    to: list[str]
    content: str
    title: str = ""


@dataclass
class ParsedReply:
    visible_text: str
    directives: list[Directive] = field(default_factory=list)
    done: str | None = None


def parse_reply(text: str) -> ParsedReply:
    found: list[tuple[int, Directive]] = []
    for m in _MESSAGE_RE.finditer(text):
        to = [t.strip() for t in m.group(1).split(",") if t.strip()]
        found.append((m.start(), Directive("message", to, m.group(2).strip()[:MAX_DIRECTIVE_CHARS])))
    for m in _TASK_RE.finditer(text):
        found.append((m.start(), Directive("task", [m.group(1).strip()], m.group(3).strip()[:MAX_DIRECTIVE_CHARS],
                                           title=(m.group(2) or "").strip()[:200])))
    directives = [d for _, d in sorted(found, key=lambda x: x[0])]  # keep source order
    done_m = _DONE_RE.search(text)
    visible = _ANY_DIRECTIVE_RE.sub("", text).strip()
    return ParsedReply(visible_text=visible, directives=directives,
                       done=done_m.group(1).strip()[:2000] if done_m else None)


def neutralize(text: str) -> str:
    """Defang directive/envelope tags inside *quoted* untrusted content so an injected
    message cannot smuggle directives or fake sender attribution into another agent's context."""
    return re.sub(r"<(/?)(message|task|done|agent_message|commander_message|kickoff)\b",
                  r"‹\1\2", text, flags=re.IGNORECASE)
