from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ..core.config import get_settings
from ..core.ratelimit import auth_limiter, client_ip
from ..core.security import create_access_token, hash_password, issue_ws_ticket, verify_password
from ..models import User
from ..plans import DEFAULT_PLANS
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from .deps import SessionDep, UserDep, audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, request: Request, session: SessionDep):
    auth_limiter.enforce(f"register:{client_ip(request)}")
    email = body.email.lower()
    if await session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, name=body.name, password_hash=hash_password(body.password),
                is_admin=email in {e.lower() for e in get_settings().admin_emails},
                credits_usd=DEFAULT_PLANS[0]["entitlements"]["monthly_credit_usd"])
    session.add(user)
    await session.flush()
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="auth.register", request=request)
    await session.commit()
    return TokenOut(token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: SessionDep):
    auth_limiter.enforce(f"login:{client_ip(request)}")
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    await audit(session, owner_id=user.id, actor=f"user:{user.id}", action="auth.login", request=request)
    await session.commit()
    return TokenOut(token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: UserDep):
    return user


@router.post("/ws-ticket")
async def ws_ticket(user: UserDep):
    """Short-lived (60s), single-use ticket for opening a WebSocket without exposing the JWT in a URL."""
    return {"ticket": issue_ws_ticket(user.id)}
