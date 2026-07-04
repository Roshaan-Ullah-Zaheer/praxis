"""Stripe Checkout + Customer Portal + webhook handling (test mode).

Every function lazily imports the ``stripe`` SDK and is gated on
``STRIPE_SECRET_KEY`` by the caller, so the rest of the app has no hard
dependency on Stripe and the demo runs without it.
"""

from __future__ import annotations

import logging

from .. import config
from ..store.base import Store

logger = logging.getLogger(__name__)

_PRICE_BY_TIER = {
    "pro": lambda: config.STRIPE_PRICE_PRO,
    "enterprise": lambda: config.STRIPE_PRICE_ENTERPRISE,
}


def _client():
    import stripe  # lazy — only needed when billing is configured

    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(owner_id: str, tier: str) -> str:
    resolver = _PRICE_BY_TIER.get(tier)
    price = resolver() if resolver else ""
    if not price:
        raise ValueError(f"No Stripe price configured for tier '{tier}'.")
    stripe = _client()
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        success_url=f"{config.FRONTEND_URL}/?checkout=success",
        cancel_url=f"{config.FRONTEND_URL}/pricing?checkout=cancel",
        client_reference_id=owner_id,
        metadata={"owner_id": owner_id, "tier": tier},
        subscription_data={"metadata": {"owner_id": owner_id, "tier": tier}},
    )
    return session.url


def create_portal_session(customer_id: str) -> str:
    stripe = _client()
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=f"{config.FRONTEND_URL}/"
    )
    return session.url


def handle_webhook(store: Store, payload: bytes, signature: str) -> None:
    """Verify the Stripe signature and reconcile the subscriptions table."""
    stripe = _client()
    event = stripe.Webhook.construct_event(payload, signature, config.STRIPE_WEBHOOK_SECRET)
    event_type = event["type"]
    obj = event["data"]["object"]
    metadata = obj.get("metadata") or {}
    owner_id = obj.get("client_reference_id") or metadata.get("owner_id")

    if event_type == "checkout.session.completed":
        if owner_id:
            store.upsert_subscription(
                owner_id,
                tier=metadata.get("tier", "pro"),
                status="active",
                stripe_customer_id=obj.get("customer"),
                stripe_subscription_id=obj.get("subscription"),
            )
    elif event_type == "customer.subscription.updated":
        if owner_id:
            store.upsert_subscription(
                owner_id,
                tier=metadata.get("tier", "pro"),
                status=obj.get("status", "active"),
                stripe_subscription_id=obj.get("id"),
            )
    elif event_type == "customer.subscription.deleted":
        if owner_id:
            store.upsert_subscription(owner_id, tier="free", status="canceled")
    else:
        logger.info("unhandled stripe event: %s", event_type)
