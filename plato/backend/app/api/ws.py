"""WebSocket endpoint: live project event stream + Commander actions.

Connect: ``GET /ws/projects/{project_id}?ticket=<one-time ticket from POST /api/auth/ws-ticket>``
Server sends a ``snapshot`` first, then every event for the project. Clients send actions:

    {"action": "user.message", "run_id": "...", "content": "...", "to": ["agent_id"] | null}
    {"action": "run.pause" | "run.resume" | "run.stop", "run_id": "..."}
    {"action": "agent.interrupt", "run_id": "...", "agent_id": "..."}
    {"action": "task.approve" | "task.reject", "run_id": "...", "task_id": "..."}
    {"action": "ping"}

Responses to actions: {"type": "ack", "ref": <client "ref">} or {"type": "error", ...}.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import db
from ..core.ratelimit import ws_message_limiter
from ..core.security import redeem_ws_ticket
from ..models import AuditLog, Project
from ..orchestrator import protocol as P
from ..orchestrator.bus import get_bus
from ..orchestrator.engine import RunError, get_run_manager

router = APIRouter()

MAX_FRAME = 64_000


@router.websocket("/ws/projects/{project_id}")
async def project_socket(ws: WebSocket, project_id: str, ticket: str = ""):
    user_id = redeem_ws_ticket(ticket)
    if not user_id:
        await ws.close(code=4401, reason="Invalid or expired ticket")
        return
    async with db.sessionmaker()() as s:
        project = await s.get(Project, project_id)
        if not project or project.owner_id != user_id:
            await ws.close(code=4404, reason="Project not found")
            return

    await ws.accept()
    sub = await get_bus().subscribe(project_id)
    runs = get_run_manager().active_for_project(project_id)
    await ws.send_json(P.envelope(P.SNAPSHOT, project_id, None, {"active_runs": [r.snapshot() for r in runs]}))

    async def pump() -> None:
        while True:
            await ws.send_json(await sub.get())

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > MAX_FRAME:
                await ws.send_json({"type": "error", "data": {"message": "Frame too large"}})
                continue
            if not ws_message_limiter.check(f"ws:{user_id}"):
                await ws.send_json({"type": "error", "data": {"message": "Rate limit exceeded"}})
                continue
            try:
                msg = json.loads(raw)
                await _handle(msg, project_id, user_id)
                await ws.send_json({"type": "ack", "ref": msg.get("ref")})
            except (RunError, ValueError, KeyError) as exc:
                await ws.send_json({"type": "error", "ref": msg.get("ref") if isinstance(msg, dict) else None,
                                    "data": {"message": str(exc)}})
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await pump_task
        await sub.close()


async def _handle(msg: dict[str, Any], project_id: str, user_id: str) -> None:
    action = msg.get("action")
    if action == "ping":
        return
    rt = get_run_manager().get(str(msg.get("run_id", "")))
    if not rt or rt.project_id != project_id or rt.owner_id != user_id:
        raise RunError("Run is not active")
    if action == "user.message":
        content = str(msg.get("content", "")).strip()
        if not content or len(content) > 20_000:
            raise ValueError("Message must be 1–20000 characters")
        to = msg.get("to")
        await rt.commander_message(content, [str(x) for x in to] if isinstance(to, list) and to else None)
    elif action == "run.pause":
        await rt.pause()
    elif action == "run.resume":
        await rt.resume()
    elif action == "run.stop":
        await rt.stop()
    elif action == "agent.interrupt":
        if not await rt.interrupt_agent(str(msg["agent_id"])):
            raise RunError("Agent is not generating")
    elif action in ("task.approve", "task.reject"):
        await rt.decide_task(str(msg["task_id"]), action == "task.approve")
    else:
        raise ValueError(f"Unknown action: {action}")
    if action != "user.message":
        async with db.sessionmaker()() as s:
            s.add(AuditLog(owner_id=user_id, actor=f"user:{user_id}", action=action, target=rt.run_id,
                           details={"via": "websocket"}))
            await s.commit()
