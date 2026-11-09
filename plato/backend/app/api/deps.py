"""Shared FastAPI dependencies: auth, tenant-scoped lookups, audit logging."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import decode_access_token
from ..db import get_session
from ..models import Agent, AuditLog, Project, Run, User

bearer = HTTPBearer(auto_error=False)
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_access_token(creds.credentials)
    user = await session.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return user


UserDep = Annotated[User, Depends(get_current_user)]


async def require_admin(user: UserDep) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required")
    return user


AdminDep = Annotated[User, Depends(require_admin)]


# Tenant isolation: every lookup checks owner_id and returns 404 (not 403) to avoid leaking existence.
async def owned_project(session: AsyncSession, user: User, project_id: str) -> Project:
    p = await session.get(Project, project_id)
    if not p or p.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return p


async def owned_agent(session: AsyncSession, user: User, agent_id: str) -> Agent:
    a = await session.get(Agent, agent_id)
    if not a or a.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return a


async def owned_run(session: AsyncSession, user: User, run_id: str) -> Run:
    r = await session.get(Run, run_id)
    if not r or r.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return r


async def audit(session: AsyncSession, *, owner_id: str | None, actor: str, action: str, target: str = "",
                details: dict[str, Any] | None = None, request: Request | None = None) -> None:
    session.add(AuditLog(owner_id=owner_id, actor=actor, action=action, target=target, details=details or {},
                         ip=request.client.host if request and request.client else None))
