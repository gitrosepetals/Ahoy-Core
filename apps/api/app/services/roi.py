from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, DailyRoiMetric

# Story 2.1: only calls longer than this count as a lead. Enforced when lead_events are rolled
# up into daily_roi_metrics.tracked_calls_count, so the count stored there is "qualified calls".
QUALIFIED_CALL_MIN_SECONDS = 60
DEFAULT_CONVERSION = Decimal("0.25")
DEFAULT_TICKET = Decimal("150.00")


def estimate_revenue(*, leads: int, conversion_rate: Decimal, average_ticket: Decimal) -> Decimal:
    """PRD Story 2.1: (qualified calls + form leads) × conversion rate × average ticket."""
    return Decimal(leads) * conversion_rate * average_ticket


def client_uses_pos(client: Client) -> bool:
    """POS attribution is a per-client switch ("if POS integration is active"), not per day."""
    return bool(client.pos_provider)


def billing_period(anchor_day: int, today: date | None = None) -> tuple[date, date]:
    """Current billing period [start, today] for a monthly cycle anchored on ``anchor_day``."""
    today = today or date.today()
    anchor = min(max(anchor_day or 1, 1), 28)
    if today.day >= anchor:
        start = today.replace(day=anchor)
    else:
        prev_month_end = today.replace(day=1) - timedelta(days=1)
        start = prev_month_end.replace(day=anchor)
    return start, today


async def summarize_roi(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    days: int | None = None,
    today: date | None = None,
) -> tuple[dict, list[dict]]:
    """Summary + per-day breakdown. ``days=None`` → current billing period (PRD default)."""
    client = (
        await db.execute(select(Client).where(Client.client_id == client_id))
    ).scalar_one()
    # "Today" is the client's local day, matching the rollup's day boundaries
    today = today or datetime.now(ZoneInfo(client.timezone or "America/Chicago")).date()
    if days is None:
        start, end = billing_period(client.billing_anchor_day, today)
        period = "billing"
    else:
        end = today
        start = end - timedelta(days=max(days - 1, 0))
        period = "rolling"

    rows = (
        await db.execute(
            select(DailyRoiMetric)
            .where(
                DailyRoiMetric.client_id == client_id,
                DailyRoiMetric.metric_date >= start,
                DailyRoiMetric.metric_date <= end,
            )
            .order_by(DailyRoiMetric.metric_date.desc())
        )
    ).scalars().all()

    conversion = client.conversion_rate_estimate or DEFAULT_CONVERSION
    ticket = client.average_ticket_value or DEFAULT_TICKET
    using_pos = client_uses_pos(client)

    total_calls = 0
    total_forms = 0
    total_reviews = 0
    total_ad = Decimal(0)
    total_pos = Decimal(0)
    total_impressions = 0
    total_clicks = 0
    total_directions = 0
    breakdown: list[dict] = []

    for row in rows:
        calls = row.tracked_calls_count or 0
        forms = row.form_leads_count or 0
        pos = row.pos_attributed_revenue_usd or Decimal(0)
        day_rev = (
            pos
            if using_pos
            else estimate_revenue(leads=calls + forms, conversion_rate=conversion, average_ticket=ticket)
        )
        total_calls += calls
        total_forms += forms
        total_reviews += row.new_reviews_count or 0
        total_ad += row.ad_spend_usd or Decimal(0)
        total_pos += pos
        total_impressions += row.impressions or 0
        total_clicks += row.clicks or 0
        total_directions += row.gbp_direction_requests or 0
        breakdown.append(
            {
                "metric_date": row.metric_date.isoformat(),
                "tracked_calls_count": calls,
                "form_leads_count": forms,
                "gbp_direction_requests": row.gbp_direction_requests or 0,
                "new_reviews_count": row.new_reviews_count or 0,
                "ad_spend_usd": float(row.ad_spend_usd or 0),
                "pos_attributed_revenue_usd": float(pos),
                "estimated_revenue_usd": float(day_rev),
                "impressions": row.impressions or 0,
                "clicks": row.clicks or 0,
            }
        )

    revenue = (
        total_pos
        if using_pos
        else estimate_revenue(
            leads=total_calls + total_forms, conversion_rate=conversion, average_ticket=ticket
        )
    )

    summary = {
        "client_id": client_id,
        "days": (end - start).days + 1,
        "period": period,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_calls": total_calls,
        "total_form_leads": total_forms,
        "total_leads": total_calls + total_forms,
        "total_reviews": total_reviews,
        "total_ad_spend_usd": float(total_ad),
        "total_pos_revenue_usd": float(total_pos),
        "estimated_revenue_usd": float(revenue),
        "using_pos": using_pos,
        "average_ticket_value": float(ticket),
        "conversion_rate_estimate": float(conversion),
        "qualified_call_min_seconds": QUALIFIED_CALL_MIN_SECONDS,
        # CL-01 "Detailed View" (vanity metrics, hidden by default in the Ship)
        "detail": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": round(total_clicks / total_impressions, 4) if total_impressions else None,
            "gbp_direction_requests": total_directions,
            "cost_per_lead_usd": (
                round(float(total_ad) / (total_calls + total_forms), 2)
                if total_calls + total_forms
                else None
            ),
        },
    }
    return summary, breakdown
