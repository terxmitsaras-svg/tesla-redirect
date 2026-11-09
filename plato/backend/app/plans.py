"""Default subscription plans and entitlement checks.

Prices are *proposed* USD prices; administrators can edit them (and entitlements) at runtime
via ``PATCH /api/admin/plans/{code}``. ``None`` means "no fixed cap" for *configuration*
counts only — AI execution is always bounded by concurrency, budget and run limits.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Agent, Plan, Project, User

DEFAULT_PLANS: list[dict[str, Any]] = [
    {
        "code": "free", "name": "Free", "price_usd_month": 0.0, "sort_order": 0,
        "entitlements": {
            "max_models": 2, "max_agents": 2, "max_projects": 1,
            "max_concurrent_agents": 2, "max_parallel_runs": 1,
            "hierarchies": False, "max_subagents_per_agent": 0,
            "monthly_credit_usd": 0.50, "max_run_seconds": 300, "max_turns_per_agent": 6,
            "max_agent_messages": 20, "external_agents": False, "persistent_memory": False,
            "team_workspaces": False, "audit_log_access": False, "priority": 0,
        },
    },
    {
        "code": "pro", "name": "Pro", "price_usd_month": 19.0, "sort_order": 1,
        "entitlements": {
            "max_models": 4, "max_agents": 8, "max_projects": 5,
            "max_concurrent_agents": 4, "max_parallel_runs": 2,
            "hierarchies": True, "max_subagents_per_agent": 3,
            "monthly_credit_usd": 5.0, "max_run_seconds": 900, "max_turns_per_agent": 12,
            "max_agent_messages": 60, "external_agents": False, "persistent_memory": False,
            "team_workspaces": False, "audit_log_access": False, "priority": 1,
        },
    },
    {
        "code": "power", "name": "Power", "price_usd_month": 49.0, "sort_order": 2,
        "entitlements": {
            "max_models": 8, "max_agents": 24, "max_projects": 25,
            "max_concurrent_agents": 8, "max_parallel_runs": 4,
            "hierarchies": True, "max_subagents_per_agent": 6,
            "monthly_credit_usd": 15.0, "max_run_seconds": 1800, "max_turns_per_agent": 20,
            "max_agent_messages": 150, "external_agents": True, "persistent_memory": True,
            "team_workspaces": False, "audit_log_access": False, "priority": 2,
        },
    },
    {
        "code": "business", "name": "Business", "price_usd_month": 149.0, "sort_order": 3,
        "entitlements": {
            "max_models": None, "max_agents": None, "max_projects": None,
            "max_concurrent_agents": 16, "max_parallel_runs": 10,
            "hierarchies": True, "max_subagents_per_agent": 12,
            "monthly_credit_usd": 50.0, "max_run_seconds": 3600, "max_turns_per_agent": 30,
            "max_agent_messages": 400, "external_agents": True, "persistent_memory": True,
            "team_workspaces": True, "audit_log_access": True, "priority": 3,
        },
    },
]


async def seed_plans(session: AsyncSession) -> None:
    existing = {p.code for p in (await session.scalars(select(Plan))).all()}
    for p in DEFAULT_PLANS:
        if p["code"] not in existing:
            session.add(Plan(**p))
    await session.commit()


async def get_entitlements(session: AsyncSession, user: User) -> dict[str, Any]:
    plan = await session.get(Plan, user.plan_code)
    if plan is None:
        plan = await session.get(Plan, "free")
    ent = dict(plan.entitlements) if plan else dict(DEFAULT_PLANS[0]["entitlements"])
    # A lapsed subscription falls back to Free entitlements.
    if user.subscription_status not in ("active", "trialing"):
        ent = dict(DEFAULT_PLANS[0]["entitlements"])
    return ent


def _deny(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"Plan limit: {msg}. Upgrade to raise this limit.")


async def check_can_create_project(session: AsyncSession, user: User) -> None:
    ent = await get_entitlements(session, user)
    cap = ent.get("max_projects")
    if cap is None:
        return
    n = await session.scalar(select(func.count()).select_from(Project).where(Project.owner_id == user.id))
    if (n or 0) >= cap:
        raise _deny(f"your plan allows {cap} project(s)")


async def check_can_create_agent(
    session: AsyncSession, user: User, *, provider: str, model: str, parent_id: str | None, kind: str
) -> None:
    ent = await get_entitlements(session, user)
    agents = (await session.scalars(select(Agent).where(Agent.owner_id == user.id))).all()

    cap = ent.get("max_agents")
    if cap is not None and len(agents) >= cap:
        raise _deny(f"your plan allows {cap} configured agent(s)")

    model_cap = ent.get("max_models")
    if model_cap is not None:
        models = {(a.provider, a.model) for a in agents}
        if (provider, model) not in models and len(models) >= model_cap:
            raise _deny(f"your plan allows {model_cap} distinct AI model(s)")

    if kind == "external" and not ent.get("external_agents"):
        raise _deny("connected external agents require the Power plan or above")

    if parent_id:
        if not ent.get("hierarchies"):
            raise _deny("agent hierarchies require the Pro plan or above")
        children = sum(1 for a in agents if a.parent_id == parent_id)
        sub_cap = ent.get("max_subagents_per_agent") or 0
        if children >= sub_cap:
            raise _deny(f"your plan allows {sub_cap} subagent(s) per agent")


async def check_can_change_model(session: AsyncSession, user: User, agent: Agent, model: str) -> None:
    ent = await get_entitlements(session, user)
    cap = ent.get("max_models")
    if cap is None:
        return
    others = (await session.scalars(select(Agent).where(Agent.owner_id == user.id, Agent.id != agent.id))).all()
    models = {(o.provider, o.model) for o in others}
    if (agent.provider, model) not in models and len(models) >= cap:
        raise _deny(f"your plan allows {cap} distinct AI model(s)")
