"""Subscription tiers, their limits, and gating helpers.

Limits mirror the pricing page. Enforcement only kicks in when billing is
configured, so the public no-login demo is never rate-limited.
"""

from __future__ import annotations

from .. import config
from ..store.base import Store

TIERS: dict[str, dict] = {
    "free": {"name": "Free", "max_documents": 5, "max_queries_per_day": 15},
    "pro": {"name": "Pro", "max_documents": 50, "max_queries_per_day": 300},
    "enterprise": {"name": "Enterprise", "max_documents": 500, "max_queries_per_day": 100000},
}


def get_tier(store: Store, owner_id: str) -> str:
    sub = store.get_subscription(owner_id)
    tier = (sub or {}).get("tier") or "free"
    return tier if tier in TIERS else "free"


def limits(tier: str) -> dict:
    return TIERS.get(tier, TIERS["free"])


def enforcement_enabled() -> bool:
    """Tier limits are only enforced when billing is configured."""
    return config.billing_enabled()


def check_can_upload(store: Store, owner_id: str) -> tuple[bool, str]:
    """Return (allowed, friendly_message). Always allowed in demo mode."""
    if not enforcement_enabled():
        return True, ""
    tier = get_tier(store, owner_id)
    cap = limits(tier)["max_documents"]
    if len(store.list_documents(owner_id)) >= cap:
        return False, (
            f"Your {limits(tier)['name']} plan includes up to {cap} documents. "
            "Upgrade your plan to add more."
        )
    return True, ""
