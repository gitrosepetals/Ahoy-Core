"""Milestone D / 0.13.0: Stripe billing (checkout, portal, ad-spend pass-through, webhooks)."""

import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import parse_qs

import httpx
import pytest
from httpx import AsyncClient

from app.config import Settings, get_settings
from app.main import app
from app.models import SubscriptionTier
from app.services import billing
from tests.helpers import CAPTAIN_PHONE, CREW_PHONE, auth_headers, sign_in_token

LIVE = Settings(
    stripe_secret_key="sk_test_x",
    stripe_webhook_secret="whsec_test",
    stripe_price_harbor="price_h",
    stripe_price_cruiser="price_c",
    stripe_price_flagship="price_f",
)


def _signed(payload: dict, secret: str = "whsec_test", ts: int | None = None) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={ts},v1={sig}"


@pytest.mark.unit
def test_signature_verification() -> None:
    body, header = _signed({"id": "evt_1"})
    assert billing.verify_signature(body, header, "whsec_test")
    assert not billing.verify_signature(body + b" ", header, "whsec_test")
    assert not billing.verify_signature(body, header, "other")
    old_body, old_header = _signed({"id": "evt_1"}, ts=int(time.time()) - 3600)
    assert not billing.verify_signature(old_body, old_header, "whsec_test")
    assert not billing.verify_signature(body, None, "whsec_test")


@pytest.mark.unit
def test_tier_price_mapping() -> None:
    assert billing.price_for_tier(LIVE, SubscriptionTier.cruiser) == "price_c"
    assert billing.tier_for_price(LIVE, "price_f") == SubscriptionTier.flagship
    assert billing.tier_for_price(LIVE, "price_unknown") is None
    with pytest.raises(billing.BillingError):
        billing.price_for_tier(Settings(), SubscriptionTier.harbor)


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_checkout_portal_and_ad_spend(client: AsyncClient, temp_client, monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        path = request.url.path
        calls.append((path, form))
        assert request.headers["authorization"].startswith("Basic ")
        if path == "/v1/customers":
            return httpx.Response(200, json={"id": "cus_123"})
        if path == "/v1/checkout/sessions":
            return httpx.Response(200, json={"url": "https://checkout.stripe.com/c/s_1"})
        if path == "/v1/billing_portal/sessions":
            return httpx.Response(200, json={"url": "https://billing.stripe.com/p/s_2"})
        if path == "/v1/invoiceitems":
            return httpx.Response(200, json={"id": "ii_9"})
        return httpx.Response(404, json={"error": {"message": "nope"}})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        billing.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    cid = str(temp_client.client_id)
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    crew = await sign_in_token(client, CREW_PHONE, "/crew")

    not_configured = await client.post(
        f"/api/v1/clients/{cid}/billing/checkout", headers=auth_headers(crew, cid), json={"tier": "cruiser"}
    )
    assert not_configured.status_code == 400

    app.dependency_overrides[get_settings] = lambda: LIVE
    try:
        checkout = await client.post(
            f"/api/v1/clients/{cid}/billing/checkout", headers=auth_headers(crew, cid), json={"tier": "cruiser"}
        )
        assert checkout.status_code == 200, checkout.text
        assert checkout.json()["url"].startswith("https://checkout.stripe.com/")
        session_form = dict(calls)["/v1/checkout/sessions"]
        assert session_form["line_items[0][price]"] == "price_c"
        assert session_form["customer"] == "cus_123"
        assert session_form["subscription_data[metadata][client_id]"] == cid

        portal = await client.post(f"/api/v1/clients/{cid}/billing/portal", headers=auth_headers(captain, cid))
        assert portal.status_code == 200 and "billing.stripe.com" in portal.json()["url"]

        denied = await client.post(
            f"/api/v1/clients/{cid}/billing/ad-spend", headers=auth_headers(captain, cid), json={"amount_usd": 120.5}
        )
        assert denied.status_code == 403
        ad = await client.post(
            f"/api/v1/clients/{cid}/billing/ad-spend", headers=auth_headers(crew, cid),
            json={"amount_usd": 120.555, "description": "Meta ads Oct"},
        )
        assert ad.status_code == 200 and ad.json()["invoice_item_id"] == "ii_9"
        assert dict(calls)["/v1/invoiceitems"]["amount"] == "12056"  # cents, half-up

        info = await client.get(f"/api/v1/clients/{cid}/billing", headers=auth_headers(captain, cid))
        assert info.json()["has_customer"] is True and info.json()["billing_enabled"] is True
        # customer created once and reused
        assert [p for p, _ in calls].count("/v1/customers") == 1
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_webhook_syncs_tier_status_and_anchor(client: AsyncClient, db_session, temp_client) -> None:
    app.dependency_overrides[get_settings] = lambda: LIVE
    try:
        anchor = 1_760_000_000  # 2025-10-09 UTC
        sub_event = {
            "id": f"evt_{uuid.uuid4().hex}",
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": "sub_1", "customer": "cus_777", "status": "active",
                "billing_cycle_anchor": anchor, "current_period_end": anchor + 30 * 86400,
                "metadata": {"client_id": str(temp_client.client_id)},
                "items": {"data": [{"price": {"id": "price_f"}}]},
            }},
        }
        body, header = _signed(sub_event)
        bad = await client.post("/api/v1/webhooks/stripe", content=body, headers={"Stripe-Signature": "t=1,v1=x"})
        assert bad.status_code == 400

        ok = await client.post("/api/v1/webhooks/stripe", content=body, headers={"Stripe-Signature": header})
        assert ok.status_code == 200 and ok.json()["outcome"] == "applied"
        again = await client.post("/api/v1/webhooks/stripe", content=body, headers={"Stripe-Signature": header})
        assert again.json()["outcome"] == "duplicate"

        await db_session.refresh(temp_client)
        assert temp_client.tier == SubscriptionTier.flagship
        assert temp_client.subscription_status == "active"
        assert temp_client.stripe_customer_id == "cus_777"
        assert temp_client.billing_anchor_day == 9
        assert temp_client.current_period_end is not None

        failed = {"id": f"evt_{uuid.uuid4().hex}", "type": "invoice.payment_failed",
                  "data": {"object": {"customer": "cus_777"}}}
        body2, header2 = _signed(failed)
        await client.post("/api/v1/webhooks/stripe", content=body2, headers={"Stripe-Signature": header2})
        await db_session.refresh(temp_client)
        assert temp_client.subscription_status == "past_due"
    finally:
        app.dependency_overrides.pop(get_settings, None)
