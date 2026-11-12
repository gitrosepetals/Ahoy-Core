"""Crew onboarding: per-client settings and integration secrets (Ayrshare, GBP, …)."""

import secrets
import time
import uuid
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import select

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId
from app.models import Client
from app.schemas import (
    AyrshareCredentialBody,
    ClientSettingsOut,
    ClientSettingsUpdate,
    FacebookCredentialBody,
    GoogleLocationOut,
    IntegrationOut,
)
from app.services import review_providers as rp
from app.services.credentials import get_credential, list_providers, put_credential

router = APIRouter(prefix="/clients", tags=["integrations"])
# OAuth callback is hit by Google's redirect (no bearer token), so it lives outside /clients
oauth_router = APIRouter(prefix="/integrations", tags=["integrations"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/business.manage"

NON_NULLABLE = {
    "billing_anchor_day", "record_calls", "timezone", "average_ticket_value",
    "conversion_rate_estimate", "auto_reply_delay_hours",
}


def _settings_out(client: Client, settings) -> ClientSettingsOut:
    api = settings.public_api_base_url.rstrip("/") + settings.api_prefix
    return ClientSettingsOut(
        client_id=client.client_id,
        business_name=client.business_name,
        twilio_tracking_number=client.twilio_tracking_number,
        gbp_location_id=client.gbp_location_id,
        pos_provider=client.pos_provider,
        average_ticket_value=float(client.average_ticket_value or 0),
        conversion_rate_estimate=float(client.conversion_rate_estimate or 0),
        billing_anchor_day=client.billing_anchor_day,
        forward_to_number=client.forward_to_number,
        record_calls=client.record_calls,
        timezone=client.timezone,
        auto_reply_delay_hours=client.auto_reply_delay_hours,
        facebook_page_id=client.facebook_page_id,
        yelp_business_id=client.yelp_business_id,
        lead_form_key=client.lead_form_key,
        lead_form_url=f"{api}/webhooks/forms/{client.lead_form_key}" if client.lead_form_key else None,
        twilio_voice_webhook_url=f"{api}/webhooks/twilio/voice",
    )


@router.get("/{client_id}/settings", response_model=ClientSettingsOut)
async def get_client_settings(
    client_id: TenantClientId, db: DbSession, settings: AppSettings, _crew: CrewUser
) -> ClientSettingsOut:
    client = (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()
    if not client.lead_form_key:
        client.lead_form_key = secrets.token_urlsafe(18)
        await db.commit()
        await db.refresh(client)
    return _settings_out(client, settings)


@router.patch("/{client_id}/settings", response_model=ClientSettingsOut)
async def update_client_settings(
    client_id: TenantClientId,
    body: ClientSettingsUpdate,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> ClientSettingsOut:
    client = (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()
    if "timezone" in body.model_fields_set:
        try:
            ZoneInfo(body.timezone or "")
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Unknown timezone") from exc
    for name in body.model_fields_set:
        value = getattr(body, name)
        if value is None and name in NON_NULLABLE:
            continue
        if name in ("average_ticket_value", "conversion_rate_estimate") and value is not None:
            value = Decimal(str(value))
        if isinstance(value, str):
            value = value.strip() or None
        setattr(client, name, value)
    if client.twilio_tracking_number:
        clash = (
            await db.execute(
                select(Client.client_id).where(
                    Client.twilio_tracking_number == client.twilio_tracking_number,
                    Client.client_id != client_id,
                )
            )
        ).first()
        if clash:
            raise HTTPException(status_code=409, detail="Tracking number already used by another client")
    await db.commit()
    await db.refresh(client)
    return _settings_out(client, settings)


@router.get("/{client_id}/integrations", response_model=list[IntegrationOut])
async def list_integrations(
    client_id: TenantClientId, db: DbSession, _crew: CrewUser
) -> list[IntegrationOut]:
    rows = await list_providers(db, client_id)
    return [IntegrationOut(provider=r.provider, connected=True, updated_at=r.updated_at) for r in rows]


@router.put("/{client_id}/integrations/ayrshare", response_model=IntegrationOut)
async def put_ayrshare(
    client_id: TenantClientId,
    body: AyrshareCredentialBody,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> IntegrationOut:
    row = await put_credential(
        db, settings, client_id, "ayrshare", {"profile_key": body.profile_key.strip()}
    )
    await db.commit()
    await db.refresh(row)
    return IntegrationOut(provider=row.provider, connected=True, updated_at=row.updated_at)


@router.put("/{client_id}/integrations/facebook", response_model=IntegrationOut)
async def put_facebook(
    client_id: TenantClientId,
    body: FacebookCredentialBody,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> IntegrationOut:
    """Page id + long-lived Page access token (pages_read_user_content, pages_manage_engagement)."""
    client = (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()
    client.facebook_page_id = body.page_id.strip()
    row = await put_credential(
        db, settings, client_id, "facebook", {"page_access_token": body.page_access_token.strip()}
    )
    await db.commit()
    await db.refresh(row)
    return IntegrationOut(provider=row.provider, connected=True, updated_at=row.updated_at)


@router.get("/{client_id}/integrations/google/start")
async def google_oauth_start(
    client_id: TenantClientId, settings: AppSettings, _crew: CrewUser
) -> dict:
    """Crew opens the returned URL; the business owner signs in to Google and grants access."""
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID is not configured")
    state = jwt.encode(
        {"client_id": str(client_id), "purpose": "google_oauth", "exp": int(time.time()) + 900},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",  # always return a refresh token
            "state": state,
        }
    )
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{query}"}


@oauth_router.get("/google/callback")
async def google_oauth_callback(
    db: DbSession,
    settings: AppSettings,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    try:
        claims = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc
    if claims.get("purpose") != "google_oauth":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    client_id = uuid.UUID(claims["client_id"])
    try:
        tokens = await rp.google_exchange_code(settings, code)
    except rp.ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not tokens.get("refresh_token"):
        raise HTTPException(status_code=400, detail="Google returned no refresh token; retry")
    await put_credential(db, settings, client_id, "google", {"refresh_token": tokens["refresh_token"]})
    await db.commit()
    return RedirectResponse(
        f"{settings.crew_app_base_url.rstrip('/')}/crew/clients/{client_id}?google=connected"
    )


@router.get("/{client_id}/integrations/google/locations", response_model=list[GoogleLocationOut])
async def google_locations(
    client_id: TenantClientId, db: DbSession, settings: AppSettings, _crew: CrewUser
) -> list[GoogleLocationOut]:
    """Pick-list for the client's ``gbp_location_id`` (accounts/…/locations/…)."""
    creds = await get_credential(db, settings, client_id, "google")
    if not creds:
        raise HTTPException(status_code=400, detail="Connect Google first")
    try:
        token = await rp.google_access_token(settings, creds["refresh_token"])
        return [GoogleLocationOut(**loc) for loc in await rp.google_list_locations(token)]
    except rp.ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
