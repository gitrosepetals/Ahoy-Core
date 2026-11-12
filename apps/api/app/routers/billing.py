import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId, require_roles
from app.models import Client, UserRole
from app.schemas import AdSpendBody, AuthUser, BillingOut, CheckoutBody, UrlOut
from app.services import billing

router = APIRouter(tags=["billing"])
ViewerUser = Depends(require_roles(UserRole.captain, UserRole.crew))


async def _client(db, client_id) -> Client:
    return (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()


@router.get("/clients/{client_id}/billing", response_model=BillingOut)
async def get_billing(
    client_id: TenantClientId, db: DbSession, settings: AppSettings, _user: AuthUser = ViewerUser
) -> BillingOut:
    client = await _client(db, client_id)
    return BillingOut(
        tier=client.tier.value,
        subscription_status=client.subscription_status,
        current_period_end=client.current_period_end,
        has_customer=bool(client.stripe_customer_id),
        billing_enabled=billing.billing_enabled(settings),
    )


@router.post("/clients/{client_id}/billing/checkout", response_model=UrlOut)
async def create_checkout(
    client_id: TenantClientId,
    body: CheckoutBody,
    db: DbSession,
    settings: AppSettings,
    _user: AuthUser = ViewerUser,
) -> UrlOut:
    """Stripe Checkout link for a tier (Crew sends it, or the Captain opens it in the Ship)."""
    client = await _client(db, client_id)
    try:
        url = await billing.create_checkout_link(db, settings, client, body.tier)
    except billing.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return UrlOut(url=url)


@router.post("/clients/{client_id}/billing/portal", response_model=UrlOut)
async def create_portal(
    client_id: TenantClientId, db: DbSession, settings: AppSettings, _user: AuthUser = ViewerUser
) -> UrlOut:
    """Stripe customer portal: update card, see invoices, cancel."""
    client = await _client(db, client_id)
    try:
        return UrlOut(url=await billing.create_portal_link(db, settings, client))
    except billing.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/clients/{client_id}/billing/ad-spend")
async def pass_through_ad_spend(
    client_id: TenantClientId,
    body: AdSpendBody,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> dict:
    client = await _client(db, client_id)
    try:
        item_id = await billing.add_ad_spend(
            db, settings, client, amount_usd=Decimal(str(body.amount_usd)), description=body.description
        )
    except billing.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {"invoice_item_id": item_id}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: DbSession, settings: AppSettings) -> dict:
    payload = await request.body()
    if not billing.verify_signature(
        payload, request.headers.get("Stripe-Signature"), settings.stripe_webhook_secret
    ):
        raise HTTPException(status_code=400, detail="Bad Stripe signature")
    outcome = await billing.handle_event(db, settings, json.loads(payload))
    await db.commit()
    return {"received": True, "outcome": outcome}
