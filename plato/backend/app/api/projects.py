"""Projects, shared workspace files, and agent configuration."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, select

from ..models import Agent, Project, ProjectFile, ProviderCredential
from ..plans import check_can_change_model, check_can_create_agent, check_can_create_project
from ..providers.base import ProviderError
from ..providers.external_adapter import validate_external_url
from ..providers.registry import get_adapter
from ..schemas import AgentIn, AgentOut, AgentPatch, FileIn, FileOut, ProjectIn, ProjectOut, ProjectPatch
from .deps import SessionDep, UserDep, audit, owned_agent, owned_project

router = APIRouter(prefix="/api", tags=["projects"])


# ---------------------------------------------------------------- projects
@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(user: UserDep, session: SessionDep):
    return (await session.scalars(select(Project).where(Project.owner_id == user.id)
                                  .order_by(Project.created_at.desc()))).all()


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectIn, request: Request, user: UserDep, session: SessionDep):
    await check_can_create_project(session, user)
    p = Project(owner_id=user.id, name=body.name, description=body.description,
                shared_context=body.shared_context, settings=body.settings.model_dump())
    session.add(p)
    await session.flush()
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="project.create", target=p.id,
                request=request)
    await session.commit()
    return p


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, user: UserDep, session: SessionDep):
    return await owned_project(session, user, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectPatch, user: UserDep, session: SessionDep):
    p = await owned_project(session, user, project_id)
    data = body.model_dump(exclude_unset=True)
    if "settings" in data and body.settings is not None:
        p.settings = body.settings.model_dump()
        data.pop("settings")
    for k, v in data.items():
        setattr(p, k, v)
    await session.commit()
    await session.refresh(p)
    return p


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, request: Request, user: UserDep, session: SessionDep):
    from ..orchestrator.engine import get_run_manager

    p = await owned_project(session, user, project_id)
    if get_run_manager().active_for_project(project_id):
        raise HTTPException(409, "Stop the active run before deleting this project")
    await session.delete(p)
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="project.delete", target=project_id,
                request=request)
    await session.commit()


# ---------------------------------------------------------------- files
@router.get("/projects/{project_id}/files", response_model=list[FileOut])
async def list_files(project_id: str, user: UserDep, session: SessionDep):
    await owned_project(session, user, project_id)
    return (await session.scalars(select(ProjectFile).where(ProjectFile.project_id == project_id)
                                  .order_by(ProjectFile.path))).all()


@router.put("/projects/{project_id}/files", response_model=FileOut)
async def upsert_file(project_id: str, body: FileIn, user: UserDep, session: SessionDep):
    await owned_project(session, user, project_id)
    f = await session.scalar(select(ProjectFile).where(ProjectFile.project_id == project_id,
                                                       ProjectFile.path == body.path))
    if f:
        f.content, f.shared_with_agents = body.content, body.shared_with_agents
    else:
        f = ProjectFile(owner_id=user.id, project_id=project_id, path=body.path, content=body.content,
                        shared_with_agents=body.shared_with_agents)
        session.add(f)
    await session.commit()
    await session.refresh(f)
    return f


@router.delete("/projects/{project_id}/files/{file_id}", status_code=204)
async def delete_file(project_id: str, file_id: str, user: UserDep, session: SessionDep):
    await owned_project(session, user, project_id)
    f = await session.get(ProjectFile, file_id)
    if not f or f.project_id != project_id:
        raise HTTPException(404, "File not found")
    await session.delete(f)
    await session.commit()


# ---------------------------------------------------------------- agents
@router.get("/projects/{project_id}/agents", response_model=list[AgentOut])
async def list_agents(project_id: str, user: UserDep, session: SessionDep):
    await owned_project(session, user, project_id)
    return (await session.scalars(select(Agent).where(Agent.project_id == project_id)
                                  .order_by(Agent.created_at))).all()


@router.post("/projects/{project_id}/agents", response_model=AgentOut, status_code=201)
async def create_agent(project_id: str, body: AgentIn, request: Request, user: UserDep, session: SessionDep):
    await owned_project(session, user, project_id)
    try:
        adapter = get_adapter(body.provider)
    except ProviderError as exc:
        raise HTTPException(400, str(exc)) from exc
    kind = "external" if adapter.info.integration == "external" else "hosted"
    if body.kind != kind:
        raise HTTPException(400, f"Provider '{body.provider}' is a {kind} integration")
    if kind == "external":
        if not body.external_url:
            raise HTTPException(400, "External agents need an endpoint URL")
        try:
            await validate_external_url(body.external_url)
        except ProviderError as exc:
            raise HTTPException(400, str(exc)) from exc

    if await session.scalar(select(Agent).where(Agent.project_id == project_id,
                                                func.lower(Agent.name) == body.name.lower())):
        raise HTTPException(409, "An agent with this name already exists in the project")
    if body.parent_id:
        parent = await owned_agent(session, user, body.parent_id)
        if parent.project_id != project_id:
            raise HTTPException(400, "Parent agent must be in the same project")
        if parent.parent_id is not None:
            raise HTTPException(400, "Subagents cannot have their own subagents (max depth: 2)")
    if body.credential_id:
        cred = await session.get(ProviderCredential, body.credential_id)
        if not cred or cred.owner_id != user.id or cred.provider != body.provider:
            raise HTTPException(400, "Credential not found for this provider")

    await check_can_create_agent(session, user, provider=body.provider, model=body.model,
                                 parent_id=body.parent_id, kind=kind)
    a = Agent(owner_id=user.id, project_id=project_id, **body.model_dump())
    session.add(a)
    await session.flush()
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="agent.create", target=a.id,
                details={"provider": a.provider, "model": a.model, "parent_id": a.parent_id}, request=request)
    await session.commit()
    await session.refresh(a)
    return a


@router.patch("/agents/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, body: AgentPatch, user: UserDep, session: SessionDep):
    a = await owned_agent(session, user, agent_id)
    data = body.model_dump(exclude_unset=True)
    if "credential_id" in data and data["credential_id"]:
        cred = await session.get(ProviderCredential, data["credential_id"])
        if not cred or cred.owner_id != user.id or cred.provider != a.provider:
            raise HTTPException(400, "Credential not found for this provider")
    if "model" in data and data["model"] != a.model:
        await check_can_change_model(session, user, a, data["model"])
    for k, v in data.items():
        setattr(a, k, v)
    await session.commit()
    await session.refresh(a)
    return a


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, request: Request, user: UserDep, session: SessionDep):
    a = await owned_agent(session, user, agent_id)
    children = (await session.scalars(select(Agent).where(Agent.parent_id == agent_id))).all()
    for c in children:
        await session.delete(c)
    await session.delete(a)
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="agent.delete", target=agent_id,
                request=request)
    await session.commit()
