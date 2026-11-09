"""Token pricing used for budgets and usage metering.

Only Anthropic list prices are built in (USD per million tokens, from Anthropic's published
table as of 2026-10). Every other model uses a conservative FALLBACK estimate unless the operator
supplies real prices via ``PLATO_MODEL_PRICING_JSON``. Costs are always flagged as estimates
in the UI; the provider's invoice is authoritative.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..core.config import get_settings

FALLBACK_PRICE: tuple[float, float] = (5.0, 20.0)

BUILTIN_PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.0, 5.0),
}


@lru_cache
def _prices() -> dict[str, tuple[float, float]]:
    prices = dict(BUILTIN_PRICES)
    raw = get_settings().model_pricing_json
    if raw:
        for model, pair in json.loads(raw).items():
            prices[model] = (float(pair[0]), float(pair[1]))
    return prices


def price_for(provider: str, model: str) -> tuple[float, float, bool]:
    """Return (input $/MTok, output $/MTok, is_known_price).

    ``PLATO_MODEL_PRICING_JSON`` keys may be ``"provider:model"`` (preferred, since the same open
    model is priced differently by Groq, Together, Hugging Face…) or a bare ``"model"``.
    """
    if provider == "mock":
        return 0.0, 0.0, True
    prices = _prices()
    p = prices.get(f"{provider}:{model}") or prices.get(model)
    if p:
        return p[0], p[1], True
    return FALLBACK_PRICE[0], FALLBACK_PRICE[1], False


def cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> tuple[float, bool]:
    inp, out, known = price_for(provider, model)
    return (input_tokens * inp + output_tokens * out) / 1_000_000, known
