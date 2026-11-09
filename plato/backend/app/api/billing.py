"""Subscriptions (Stripe Checkout + Customer Portal + webhooks), usage metering and plan admin.

Upgrades/downgrades/cancellation happen in Stripe's Customer Portal; PLATO applies the result
from signed webhooks, which are the single source of truth for a user's plan.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import Integer, func, select

from ..core.config import get_settings
from ..models import AuditLog, Plan, UsageRecord, User
from ..plans import get_entitlements
from ..schemas import CheckoutIn, PlanOut, PlanPatch
from .deps import AdminDep, SessionDep, UserDep, audit

log = logging.getLogger("plato.billing")
router = APIRouter(prefix="/api", tags=["billing"])


def _stripe() -> Any:
    s = get_settings()
    if not s.stripe_secret_key:
        raise HTTPException(503, "Stripe is not configured on this server (set PLATO_STRIPE_SECRET_KEY)")
    stripe.api_key = s.stripe_secret_key
    return stripe


@router.get("/billing/plans", response_model=list[PlanOut])
async def plans(session: SessionDep):
    return (await session.scalars(select(Plan).order_by(Plan.sort_order))).all()


@router.get("/billing/summary")
async def summary(user: UserDep, session: SessionDep):
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = (await session.execute(
        select(UsageRecord.provider, UsageRecord.model, UsageRecord.billed_to,
               func.sum(UsageRecord.input_tokens), func.sum(UsageRecord.output_tokens),
               func.sum(UsageRecord.cost_usd), func.count(), func.max(UsageRecord.cost_is_estimate.cast(Integer)))
        .where(UsageRecord.owner_id == user.id, UsageRecord.created_at >= month_start)
        .group_by(UsageRecord.provider, UsageRecord.model, UsageRecord.billed_to)
    )).all()
    by_model = [{"provider": r[0], "model": r[1], "billed_to": r[2], "input_tokens": int(r[3] or 0),
                 "output_tokens": int(r[4] or 0), "cost_usd": round(float(r[5] or 0), 6), "calls": int(r[6]),
                 "price_is_fallback_estimate": bool(r[7])} for r in rows]
    plan = await session.get(Plan, user.plan_code)
    return {
        "plan": PlanOut.model_validate(plan).model_dump() if plan else None,
        "subscription_status": user.subscription_status,
        "credits_usd": round(user.credits_usd, 4),
        "entitlements": await get_entitlements(session, user),
        "month_start": month_start.isoformat(),
        "usage_by_model": by_model,
        "total_cost_usd": round(sum(m["cost_usd"] for m in by_model), 6),
        "stripe_enabled": bool(get_settings().stripe_secret_key),
        "pricing_note": "Costs are estimates from list prices; your provider's invoice is authoritative. "
                        "BYOK usage is billed by the provider to your own account.",
    }


@router.post("/billing/checkout")
async def checkout(body: CheckoutIn, user: UserDep, session: SessionDep):
    st = _stripe()
    plan = await session.get(Plan, body.plan_code)
    if not plan or plan.price_usd_month <= 0:
        raise HTTPException(400, "Choose a paid plan")
    if not plan.stripe_price_id:
        raise HTTPException(400, f"Plan '{plan.code}' has no Stripe price configured (admin: set stripe_price_id)")
    if user.stripe_subscription_id and user.subscription_status in ("active", "trialing"):
        raise HTTPException(409, "You already have a subscription. Use the billing portal to change plans.")
    if not user.stripe_customer_id:
        customer = st.Customer.create(email=user.email, metadata={"plato_user_id": user.id})
        user.stripe_customer_id = customer.id
        await session.commit()
    app = get_settings().public_app_url
    sess = st.checkout.Session.create(
        mode="subscription", customer=user.stripe_customer_id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=f"{app}/billing?checkout=success", cancel_url=f"{app}/billing?checkout=cancelled",
        client_reference_id=user.id, metadata={"plato_user_id": user.id, "plan_code": plan.code},
        subscription_data={"metadata": {"plato_user_id": user.id, "plan_code": plan.code}},
    )
    return {"url": sess.url}


@router.post("/billing/portal")
async def portal(user: UserDep):
    st = _stripe()
    if not user.stripe_customer_id:
        raise HTTPException(400, "No billing account yet — subscribe to a plan first")
    sess = st.billing_portal.Session.create(customer=user.stripe_customer_id,
                                            return_url=f"{get_settings().public_app_url}/billing")
    return {"url": sess.url}


async def _plan_for_price(session, price_id: str | None) -> Plan | None:
    if not price_id:
        return None
    return await session.scalar(select(Plan).where(Plan.stripe_price_id == price_id))


@router.post("/billing/webhook")
async def webhook(request: Request, session: SessionDep):
    s = get_settings()
    if not s.stripe_webhook_secret:
        raise HTTPException(503, "Stripe webhooks are not configured")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""),
                                               s.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid signature") from exc

    event = event.to_dict()  # StripeObject -> plain dict (stripe-python >= 13)
    etype = event["type"]
    obj = event["data"]["object"]
    user: User | None = None
    if etype == "checkout.session.completed":
        uid = (obj.get("metadata") or {}).get("plato_user_id") or obj.get("client_reference_id")
        user = await session.get(User, uid) if uid else None
        if user:
            user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
            user.stripe_subscription_id = obj.get("subscription") or user.stripe_subscription_id
            code = (obj.get("metadata") or {}).get("plan_code")
            if code and await session.get(Plan, code):
                user.plan_code, user.subscription_status = code, "active"
    elif etype in ("customer.subscription.created", "customer.subscription.updated"):
        user = await session.scalar(select(User).where(User.stripe_customer_id == obj.get("customer")))
        if user:
            items = (obj.get("items") or {}).get("data") or []
            plan = await _plan_for_price(session, items[0]["price"]["id"] if items else None)
            if plan:
                user.plan_code = plan.code
            user.stripe_subscription_id = obj.get("id")
            user.subscription_status = obj.get("status", user.subscription_status)
    elif etype == "customer.subscription.deleted":
        user = await session.scalar(select(User).where(User.stripe_customer_id == obj.get("customer")))
        if user:
            user.plan_code, user.subscription_status, user.stripe_subscription_id = "free", "active", None
    elif etype == "invoice.paid":
        user = await session.scalar(select(User).where(User.stripe_customer_id == obj.get("customer")))
        if user:  # monthly platform-credit allowance (does not roll over)
            ent = await get_entitlements(session, user)
            user.credits_usd = max(user.credits_usd, float(ent.get("monthly_credit_usd") or 0))

    session.add(AuditLog(owner_id=user.id if user else None, actor="stripe", action=f"stripe.{etype}",
                         target=event.get("id", ""), details={"handled": bool(user)}))
    await session.commit()
    return {"received": True}


# ---------------------------------------------------------------- admin
@router.patch("/admin/plans/{code}", response_model=PlanOut)
async def update_plan(code: str, body: PlanPatch, request: Request, admin: AdminDep, session: SessionDep):
    plan = await session.get(Plan, code)
    if not plan:
        raise HTTPException(404, "Plan not found")
    data = body.model_dump(exclude_unset=True)
    if "entitlements" in data:
        plan.entitlements = {**plan.entitlements, **data.pop("entitlements")}
    for k, v in data.items():
        setattr(plan, k, v)
    await audit(session, owner_id=admin.id, actor=f"user:{admin.id}", action="admin.plan.update", target=code,
                details=body.model_dump(exclude_unset=True), request=request)
    await session.commit()
    await session.refresh(plan)
    return plan


@router.get("/audit-logs")
async def audit_logs(user: UserDep, session: SessionDep, limit: int = 100):
    ent = await get_entitlements(session, user)
    if not (ent.get("audit_log_access") or user.is_admin):
        raise HTTPException(402, "Audit log access requires the Business plan")
    rows = (await session.scalars(select(AuditLog).where(AuditLog.owner_id == user.id)
                                  .order_by(AuditLog.created_at.desc()).limit(min(limit, 500)))).all()
    return [{"id": r.id, "actor": r.actor, "action": r.action, "target": r.target, "details": r.details,
             "ip": r.ip, "created_at": r.created_at.isoformat()} for r in rows]
