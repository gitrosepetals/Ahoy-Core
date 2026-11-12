import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.deps import AppSettings, CrewUser, DbSession, TenantClientId, require_roles
from app.models import Client, DailyRoiMetric, LeadEvent, LeadEventType, UserRole
from app.schemas import AuthUser, LeadEventOut, ManualMetricsBody, RoiDayRow, RoiSummary
from app.services.leads import is_qualified_call, list_lead_events
from app.services.roi import (
    DEFAULT_CONVERSION,
    DEFAULT_TICKET,
    billing_period,
    client_uses_pos,
    estimate_revenue,
    summarize_roi,
)

router = APIRouter(prefix="/clients", tags=["roi"])

ViewerUser = Depends(require_roles(UserRole.captain, UserRole.crew))


@router.get("/{client_id}/roi", response_model=RoiSummary)
async def get_roi(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = ViewerUser,
    days: int | None = Query(default=None, ge=1, le=90),
) -> RoiSummary:
    summary, _ = await summarize_roi(db, client_id, days=days)
    return RoiSummary(**summary)


@router.get("/{client_id}/roi/breakdown", response_model=list[RoiDayRow])
async def get_roi_breakdown(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = ViewerUser,
    days: int | None = Query(default=None, ge=1, le=90),
) -> list[RoiDayRow]:
    _, breakdown = await summarize_roi(db, client_id, days=days)
    return [RoiDayRow(**row) for row in breakdown]


def _lead_out(e: LeadEvent) -> LeadEventOut:
    meta = e.meta or {}
    is_call = e.event_type == LeadEventType.tracked_call
    return LeadEventOut(
        event_id=e.event_id,
        event_type=e.event_type.value,
        occurred_at=e.occurred_at,
        duration_seconds=e.duration_seconds,
        qualified=is_qualified_call(e.duration_seconds) if is_call else True,
        caller=meta.get("from") if is_call else None,
        call_status=meta.get("status") if is_call else None,
        has_recording=bool(meta.get("recording_url")),
        name=meta.get("name"),
        email=meta.get("email"),
        phone=meta.get("phone"),
        message=meta.get("message"),
    )


@router.get("/{client_id}/roi/leads", response_model=list[LeadEventOut])
async def get_roi_leads(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = ViewerUser,
    days: int | None = Query(default=None, ge=1, le=90),
) -> list[LeadEventOut]:
    """Story 2.1: the exact calls and form submissions behind the revenue number."""
    client = (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()
    tz = ZoneInfo(client.timezone or "America/Chicago")
    if days is None:
        start, _ = billing_period(client.billing_anchor_day, datetime.now(tz).date())
    else:
        start = datetime.now(tz).date() - timedelta(days=days - 1)
    since = datetime.combine(start, time.min, tz)
    events = await list_lead_events(db, client_id, since=since)
    return [_lead_out(e) for e in events]


@router.get("/{client_id}/leads/{event_id}/recording")
async def get_call_recording(
    client_id: TenantClientId,
    event_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    _user: AuthUser = ViewerUser,
) -> Response:
    """Proxy the Twilio recording (Twilio media URLs require account auth)."""
    event = (
        await db.execute(
            select(LeadEvent).where(LeadEvent.event_id == event_id, LeadEvent.client_id == client_id)
        )
    ).scalar_one_or_none()
    url = (event.meta or {}).get("recording_url") if event else None
    if not url:
        raise HTTPException(status_code=404, detail="No recording for this call")
    if not url.startswith("https://api.twilio.com/"):
        raise HTTPException(status_code=400, detail="Unexpected recording host")
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        res = await client.get(
            f"{url}.mp3", auth=(settings.twilio_account_sid, settings.twilio_auth_token)
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail="Recording unavailable from Twilio")
    return Response(content=res.content, media_type="audio/mpeg")


@router.put("/{client_id}/roi/manual", response_model=RoiDayRow)
async def put_manual_metrics(
    client_id: TenantClientId,
    body: ManualMetricsBody,
    db: DbSession,
    _crew: CrewUser,
) -> RoiDayRow:
    """Crew concierge entry for one day (ad spend, impressions/clicks, directions, POS $)."""
    values: dict = {}
    for name in ("impressions", "clicks", "gbp_direction_requests"):
        if getattr(body, name) is not None:
            values[name] = getattr(body, name)
    for name in ("ad_spend_usd", "pos_attributed_revenue_usd"):
        if getattr(body, name) is not None:
            values[name] = Decimal(str(getattr(body, name)))
    if not values:
        raise HTTPException(status_code=400, detail="Nothing to update")
    stmt = insert(DailyRoiMetric).values(client_id=client_id, metric_date=body.metric_date, **values)
    await db.execute(stmt.on_conflict_do_update(index_elements=["client_id", "metric_date"], set_=values))
    await db.commit()

    row = (
        await db.execute(
            select(DailyRoiMetric).where(
                DailyRoiMetric.client_id == client_id, DailyRoiMetric.metric_date == body.metric_date
            )
        )
    ).scalar_one()
    await db.refresh(row)
    client = (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()
    calls, forms = row.tracked_calls_count or 0, row.form_leads_count or 0
    revenue = (
        row.pos_attributed_revenue_usd or Decimal(0)
        if client_uses_pos(client)
        else estimate_revenue(
            leads=calls + forms,
            conversion_rate=client.conversion_rate_estimate or DEFAULT_CONVERSION,
            average_ticket=client.average_ticket_value or DEFAULT_TICKET,
        )
    )
    return RoiDayRow(
        metric_date=row.metric_date.isoformat(),
        tracked_calls_count=calls,
        form_leads_count=forms,
        gbp_direction_requests=row.gbp_direction_requests or 0,
        new_reviews_count=row.new_reviews_count or 0,
        ad_spend_usd=float(row.ad_spend_usd or 0),
        pos_attributed_revenue_usd=float(row.pos_attributed_revenue_usd or 0),
        estimated_revenue_usd=float(revenue),
        impressions=row.impressions or 0,
        clicks=row.clicks or 0,
    )

