"""Stripe Billing (PRD §4): subscription ↔ ``clients.tier`` and ad-spend pass-through.

Uses Stripe's REST API directly (form-encoded) — the handful of calls we need doesn't
justify the SDK. Webhooks are the source of truth for tier / status / billing period.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Client, StripeEvent, SubscriptionTier, User
from app.services.audit import Actor, record

logger = logging.getLogger(__name__)

STRIPE_API = "https://api.stripe.com/v1"
SIGNATURE_TOLERANCE_SECONDS = 300


class BillingError(Exception):
    pass


def billing_enabled(settings: Settings) -> bool:
    return bool(settings.stripe_secret_key)


def price_for_tier(settings: Settings, tier: SubscriptionTier) -> str:
    price = {
        SubscriptionTier.harbor: settings.stripe_price_harbor,
        SubscriptionTier.cruiser: settings.stripe_price_cruiser,
        SubscriptionTier.flagship: settings.stripe_price_flagship,
    }[tier]
    if not price:
        raise BillingError(f"No Stripe price configured for {tier.value}")
    return price


def tier_for_price(settings: Settings, price_id: str | None) -> SubscriptionTier | None:
    mapping = {
        settings.stripe_price_harbor: SubscriptionTier.harbor,
        settings.stripe_price_cruiser: SubscriptionTier.cruiser,
        settings.stripe_price_flagship: SubscriptionTier.flagship,
    }
    return mapping.get(price_id or "") if price_id else None


async def _stripe(settings: Settings, method: str, path: str, data: dict | None = None) -> dict:
    if not billing_enabled(settings):
        raise BillingError("Stripe is not configured (STRIPE_SECRET_KEY)")
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.request(
            method,
            f"{STRIPE_API}{path}",
            auth=(settings.stripe_secret_key, ""),
            data=data,
            headers={"Idempotency-Key": str(uuid.uuid4())} if method == "POST" else None,
        )
    body = res.json() if res.content else {}
    if res.status_code >= 400:
        raise BillingError(f"Stripe {res.status_code}: {(body.get('error') or {}).get('message', res.text[:200])}")
    return body


async def ensure_customer(db: AsyncSession, settings: Settings, client: Client) -> str:
    if client.stripe_customer_id:
        return client.stripe_customer_id
    owner = await db.get(User, client.owner_user_id)
    customer = await _stripe(
        settings,
        "POST",
        "/customers",
        {
            "name": client.business_name,
            "email": owner.email if owner else "",
            "phone": (owner.phone_number or "") if owner else "",
            "metadata[client_id]": str(client.client_id),
        },
    )
    client.stripe_customer_id = customer["id"]
    await db.flush()
    return customer["id"]


async def create_checkout_link(
    db: AsyncSession, settings: Settings, client: Client, tier: SubscriptionTier
) -> str:
    customer = await ensure_customer(db, settings, client)
    base = settings.ship_app_base_url.rstrip("/")
    session = await _stripe(
        settings,
        "POST",
        "/checkout/sessions",
        {
            "mode": "subscription",
            "customer": customer,
            "line_items[0][price]": price_for_tier(settings, tier),
            "line_items[0][quantity]": "1",
            "client_reference_id": str(client.client_id),
            "subscription_data[metadata][client_id]": str(client.client_id),
            "success_url": f"{base}/ship?billing=success",
            "cancel_url": f"{base}/ship?billing=cancelled",
        },
    )
    return session["url"]


async def create_portal_link(db: AsyncSession, settings: Settings, client: Client) -> str:
    if not client.stripe_customer_id:
        raise BillingError("No subscription yet")
    session = await _stripe(
        settings,
        "POST",
        "/billing_portal/sessions",
        {"customer": client.stripe_customer_id, "return_url": f"{settings.ship_app_base_url.rstrip('/')}/ship"},
    )
    return session["url"]


async def add_ad_spend(
    db: AsyncSession, settings: Settings, client: Client, *, amount_usd: Decimal, description: str
) -> str:
    """Pass ad spend through to the client's next invoice (pending invoice item)."""
    customer = await ensure_customer(db, settings, client)
    cents = int((amount_usd * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    item = await _stripe(
        settings,
        "POST",
        "/invoiceitems",
        {
            "customer": customer,
            "amount": str(cents),
            "currency": "usd",
            "description": description,
            "metadata[client_id]": str(client.client_id),
            "metadata[kind]": "ad_spend",
        },
    )
    return item["id"]


def verify_signature(payload: bytes, header: str | None, secret: str, *, now: float | None = None) -> bool:
    """Stripe-Signature: t=<ts>,v1=<hex hmac sha256 of "t.payload">."""
    if not header or not secret:
        return False
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        key, _, value = item.strip().partition("=")
        parts.setdefault(key, []).append(value)
    try:
        ts = int(parts["t"][0])
    except (KeyError, ValueError):
        return False
    if abs((now or time.time()) - ts) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    expected = hmac.new(
        secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


async def _client_for(db: AsyncSession, obj: dict) -> Client | None:
    client_id = (obj.get("metadata") or {}).get("client_id") or obj.get("client_reference_id")
    if client_id:
        try:
            return await db.get(Client, uuid.UUID(client_id))
        except ValueError:
            return None
    customer = obj.get("customer")
    if customer:
        return (
            await db.execute(select(Client).where(Client.stripe_customer_id == customer))
        ).scalar_one_or_none()
    return None


def apply_subscription(settings: Settings, client: Client, sub: dict) -> None:
    client.stripe_subscription_id = sub.get("id")
    client.stripe_customer_id = client.stripe_customer_id or sub.get("customer")
    client.subscription_status = sub.get("status") or "none"
    items = (sub.get("items") or {}).get("data") or []
    price_id = ((items[0].get("price") or {}).get("id")) if items else None
    tier = tier_for_price(settings, price_id)
    if tier:
        client.tier = tier
    # current_period_* moved onto subscription items in newer Stripe API versions
    period_end = sub.get("current_period_end") or (items[0].get("current_period_end") if items else None)
    if period_end:
        client.current_period_end = datetime.fromtimestamp(int(period_end), UTC)
    anchor = sub.get("billing_cycle_anchor")
    if anchor:
        # Treasure Map "current billing period" follows Stripe's cycle (capped to 28 like the column)
        client.billing_anchor_day = min(datetime.fromtimestamp(int(anchor), UTC).day, 28)


async def handle_event(db: AsyncSession, settings: Settings, event: dict) -> str:
    """Apply one webhook event (idempotent by event id). Returns a short outcome."""
    event_id, event_type = event.get("id"), event.get("type", "")
    if not event_id:
        return "ignored: no id"
    if await db.get(StripeEvent, event_id):
        return "duplicate"
    db.add(StripeEvent(event_id=event_id, event_type=event_type))
    obj = (event.get("data") or {}).get("object") or {}

    client = await _client_for(db, obj)
    if client is None:
        await db.flush()
        return "ignored: unknown client"

    before = (client.tier.value, client.subscription_status)
    if event_type == "checkout.session.completed":
        client.stripe_customer_id = obj.get("customer") or client.stripe_customer_id
        client.stripe_subscription_id = obj.get("subscription") or client.stripe_subscription_id
    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        apply_subscription(settings, client, obj)
        if event_type == "customer.subscription.deleted":
            client.subscription_status = "canceled"
    elif event_type == "invoice.payment_failed":
        client.subscription_status = "past_due"
    else:
        await db.flush()
        return f"ignored: {event_type}"
    after = (client.tier.value, client.subscription_status)
    if after != before:
        record(
            db.sync_session,
            client_id=client.client_id,
            entity_type="billing",
            entity_id=client.stripe_subscription_id,
            action=event_type,
            from_status=f"{before[0]}/{before[1]}",
            to_status=f"{after[0]}/{after[1]}",
            actor=Actor(user_id=None, role="webhook"),
        )
    await db.flush()
    logger.info("Stripe %s applied to %s (%s)", event_type, client.business_name, client.subscription_status)
    return "applied"
