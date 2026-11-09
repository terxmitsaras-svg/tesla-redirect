"""Optional Stripe Billing Meter reporting for platform-managed (non-BYOK) usage."""
from __future__ import annotations

import asyncio
import logging

import stripe

from .core.config import get_settings

log = logging.getLogger("plato.billing")


async def report_platform_usage(stripe_customer_id: str | None, cost_usd: float) -> None:
    """Send one meter event, valued in hundredths of a cent, when a meter is configured."""
    s = get_settings()
    if not (s.stripe_secret_key and s.stripe_meter_event_name and stripe_customer_id) or cost_usd <= 0:
        return
    stripe.api_key = s.stripe_secret_key
    value = max(1, round(cost_usd * 10_000))
    try:
        await asyncio.to_thread(
            stripe.billing.MeterEvent.create,
            event_name=s.stripe_meter_event_name,
            payload={"stripe_customer_id": stripe_customer_id, "value": str(value)},
        )
    except Exception:  # metering must never break a run; failures are logged for reconciliation
        log.exception("failed to report usage to Stripe meter")
