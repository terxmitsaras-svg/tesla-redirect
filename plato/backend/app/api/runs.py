"""Run lifecycle, history (events/tasks) and Commander controls. Every control is also available
over the WebSocket; REST exists for scripts, tests, and reconnect-free clients."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from ..core.ratelimit import run_limiter
from ..models import Event, Run, Task
from ..orchestrator.engine import RunError, RunRuntime, get_run_manager
from ..schemas import CommanderMessageIn, EventOut, RunIn, RunOut, TaskOut
from .deps import SessionDep, UserDep, audit, owned_project, owned_run

router = APIRouter(prefix="/api", tags=["runs"])


def _live(run_id: str) -> RunRuntime:
    rt = get_run_manager().get(run_id)
    if not rt:
        raise HTTPException(409, "Run is not active")
    return rt


@router.post("/projects/{project_id}/runs", response_model=RunOut, status_code=201)
async def start_run(project_id: str, body: RunIn, request: Request, user: UserDep, session: SessionDep):
    run_limiter.enforce(f"run:{user.id}")
    project = await owned_project(session, user, project_id)
    if get_run_manager().active_for_project(project_id):
        raise HTTPException(409, "This project already has an active run. Stop it or message the team instead.")
    try:
        run = await get_run_manager().start_run(user=user, project=project, objective=body.objective,
                                                mode=body.mode, overrides=body.limits, assignments=body.assignments)
    except RunError as exc:
        raise HTTPException(400, str(exc)) from exc
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="run.start", target=run.id,
                details={"project_id": project_id, "mode": run.mode}, request=request)
    await session.commit()
    return run


@router.get("/projects/{project_id}/runs", response_model=list[RunOut])
async def list_runs(project_id: str, user: UserDep, session: SessionDep, limit: int = 20):
    await owned_project(session, user, project_id)
    return (await session.scalars(select(Run).where(Run.project_id == project_id)
                                  .order_by(Run.created_at.desc()).limit(min(limit, 100)))).all()


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: str, user: UserDep, session: SessionDep):
    return await owned_run(session, user, run_id)


@router.get("/runs/{run_id}/events", response_model=list[EventOut])
async def run_events(run_id: str, user: UserDep, session: SessionDep, after_seq: int = 0, limit: int = 2000):
    await owned_run(session, user, run_id)
    return (await session.scalars(select(Event).where(Event.run_id == run_id, Event.seq > after_seq)
                                  .order_by(Event.seq).limit(min(limit, 5000)))).all()


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
async def project_tasks(project_id: str, user: UserDep, session: SessionDep, run_id: str | None = None):
    await owned_project(session, user, project_id)
    q = select(Task).where(Task.project_id == project_id)
    if run_id:
        q = q.where(Task.run_id == run_id)
    return (await session.scalars(q.order_by(Task.created_at.desc()).limit(500))).all()


@router.post("/runs/{run_id}/messages", status_code=202)
async def commander_message(run_id: str, body: CommanderMessageIn, user: UserDep, session: SessionDep):
    await owned_run(session, user, run_id)
    try:
        await _live(run_id).commander_message(body.content, body.to)
    except RunError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@router.post("/runs/{run_id}/{action}", status_code=202)
async def control(run_id: str, action: str, request: Request, user: UserDep, session: SessionDep):
    await owned_run(session, user, run_id)
    rt = _live(run_id)
    if action == "pause":
        await rt.pause()
    elif action == "resume":
        await rt.resume()
    elif action == "stop":
        await rt.stop()
    else:
        raise HTTPException(404, "Unknown action")
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action=f"run.{action}", target=run_id,
                request=request)
    await session.commit()
    return {"ok": True}


@router.post("/runs/{run_id}/agents/{agent_id}/interrupt", status_code=202)
async def interrupt(run_id: str, agent_id: str, user: UserDep, session: SessionDep):
    await owned_run(session, user, run_id)
    if not await _live(run_id).interrupt_agent(agent_id):
        raise HTTPException(409, "Agent is not generating")
    return {"ok": True}


@router.post("/runs/{run_id}/tasks/{task_id}/{decision}", status_code=202)
async def decide(run_id: str, task_id: str, decision: str, request: Request, user: UserDep, session: SessionDep):
    await owned_run(session, user, run_id)
    if decision not in ("approve", "reject"):
        raise HTTPException(404, "Unknown decision")
    try:
        await _live(run_id).decide_task(task_id, decision == "approve")
    except RunError as exc:
        raise HTTPException(400, str(exc)) from exc
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action=f"task.{decision}", target=task_id,
                request=request)
    await session.commit()
    return {"ok": True}
