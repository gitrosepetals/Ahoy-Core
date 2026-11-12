"""Lead capture + rollup feeding the Treasure Map (CL-01 / Story 2.1).

Calls and form submissions are stored as ``lead_events``; ``rollup_daily_metrics`` turns them
(plus new reviews) into ``daily_roi_metrics`` per client-local day. Only calls lasting at least
``QUALIFIED_CALL_MIN_SECONDS`` count as leads.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Client, DailyRoiMetric, LeadEvent, LeadEventType, Review
from app.services.roi import QUALIFIED_CALL_MIN_SECONDS


def is_qualified_call(duration_seconds: int | None) -> bool:
    return (duration_seconds or 0) >= QUALIFIED_CALL_MIN_SECONDS


async def upsert_call_event(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    call_sid: str,
    duration_seconds: int | None,
    meta: dict,
    occurred_at: datetime | None = None,
) -> LeadEvent:
    """Idempotent per CallSid: Twilio retries/second callbacks update the same row."""
    existing = (
        await db.execute(
            select(LeadEvent).where(
                LeadEvent.client_id == client_id,
                LeadEvent.event_type == LeadEventType.tracked_call,
                LeadEvent.external_id == call_sid,
            )
        )
    ).scalar_one_or_none()
    if existing:
        if duration_seconds is not None:
            existing.duration_seconds = duration_seconds
        existing.meta = {**(existing.meta or {}), **{k: v for k, v in meta.items() if v}}
        await db.flush()
        return existing
    event = LeadEvent(
        client_id=client_id,
        event_type=LeadEventType.tracked_call,
        external_id=call_sid,
        duration_seconds=duration_seconds,
        meta=meta,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event


async def record_form_lead(
    db: AsyncSession, *, client_id: uuid.UUID, fields: dict, external_id: str | None = None
) -> LeadEvent:
    event = LeadEvent(
        client_id=client_id,
        event_type=LeadEventType.form_lead,
        external_id=external_id,
        meta=fields,
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event


def _local_date(ts: datetime, tz: ZoneInfo) -> date:
    return ts.astimezone(tz).date()


async def rollup_client_days(
    db: AsyncSession, client: Client, *, start: date, end: date
) -> list[date]:
    """Recompute event-derived columns for local days in [start, end] that have activity.

    Days with no events/reviews are left untouched so Crew-entered or seeded rows survive.
    """
    tz = ZoneInfo(client.timezone or "America/Chicago")
    window_start = datetime.combine(start, datetime.min.time(), tz)
    window_end = datetime.combine(end + timedelta(days=1), datetime.min.time(), tz)

    events = (
        await db.execute(
            select(LeadEvent).where(
                LeadEvent.client_id == client.client_id,
                LeadEvent.occurred_at >= window_start,
                LeadEvent.occurred_at < window_end,
            )
        )
    ).scalars().all()
    reviews = (
        await db.execute(
            select(Review.reviewed_at).where(
                Review.client_id == client.client_id,
                Review.reviewed_at >= window_start,
                Review.reviewed_at < window_end,
            )
        )
    ).scalars().all()

    days: dict[date, dict[str, int]] = {}

    def bucket(d: date) -> dict[str, int]:
        return days.setdefault(
            d, {"tracked_calls_count": 0, "form_leads_count": 0, "new_reviews_count": 0}
        )

    for e in events:
        b = bucket(_local_date(e.occurred_at, tz))
        if e.event_type == LeadEventType.tracked_call:
            if is_qualified_call(e.duration_seconds):
                b["tracked_calls_count"] += 1
        elif e.event_type == LeadEventType.form_lead:
            b["form_leads_count"] += 1
        # gbp_direction_requests is owned by the GBP Performance sync (reviews.sync_gbp_performance)
    for reviewed_at in reviews:
        bucket(_local_date(reviewed_at, tz))["new_reviews_count"] += 1

    for d, counts in days.items():
        stmt = insert(DailyRoiMetric).values(client_id=client.client_id, metric_date=d, **counts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["client_id", "metric_date"], set_=counts
        )
        await db.execute(stmt)
    await db.flush()
    return sorted(days)


async def rollup_daily_metrics(
    db: AsyncSession, _settings: Settings, *, days_back: int = 2
) -> dict:
    """Worker job: refresh today + the previous ``days_back`` days for every client."""
    clients = (await db.execute(select(Client))).scalars().all()
    touched = 0
    for client in clients:
        today = datetime.now(ZoneInfo(client.timezone or "America/Chicago")).date()
        touched += len(
            await rollup_client_days(db, client, start=today - timedelta(days=days_back), end=today)
        )
    return {"clients": len(clients), "days_updated": touched}


async def list_lead_events(
    db: AsyncSession, client_id: uuid.UUID, *, since: datetime, limit: int = 200
) -> list[LeadEvent]:
    result = await db.execute(
        select(LeadEvent)
        .where(LeadEvent.client_id == client_id, LeadEvent.occurred_at >= since)
        .order_by(LeadEvent.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

