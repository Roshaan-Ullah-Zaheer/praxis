"""Billing API: subscription status, Stripe Checkout, Customer Portal, webhook.

Checkout/portal/webhook require Stripe to be configured (otherwise 503). The
subscription endpoint always works and reports the current tier + limits, so the
frontend can show plan state even in the free/demo case.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import config
from ..auth import current_owner
from ..billing import stripe_client, tiers
from ..store import get_store

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutIn(BaseModel):
    tier: str = "pro"


@router.get("/subscription")
def get_subscription(owner: str = Depends(current_owner)) -> dict:
    store = get_store()
    tier = tiers.get_tier(store, owner)
    return {
        "tier": tier,
        "limits": tiers.limits(tier),
        "billing_enabled": config.billing_enabled(),
        "enforced": tiers.enforcement_enabled(),
    }


@router.post("/checkout")
def checkout(payload: CheckoutIn, owner: str = Depends(current_owner)) -> dict:
    if not config.billing_enabled():
        raise HTTPException(503, "Billing is not configured for this deployment.")
    try:
        url = stripe_client.create_checkout_session(owner, payload.tier)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not start checkout: {exc}")
    return {"url": url}


@router.post("/portal")
def portal(owner: str = Depends(current_owner)) -> dict:
    if not config.billing_enabled():
        raise HTTPException(503, "Billing is not configured for this deployment.")
    store = get_store()
    sub = store.get_subscription(owner)
    if not sub or not sub.get("stripe_customer_id"):
        raise HTTPException(400, "No billing account found for this user.")
    try:
        url = stripe_client.create_portal_session(sub["stripe_customer_id"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not open the billing portal: {exc}")
    return {"url": url}


@router.post("/webhook")
async def webhook(request: Request) -> dict:
    if not config.billing_enabled():
        raise HTTPException(503, "Billing is not configured for this deployment.")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        stripe_client.handle_webhook(get_store(), payload, signature)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Webhook error: {exc}")
    return {"received": True}
