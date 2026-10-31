from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, DailyRoiMetric


def estimate_day_revenue(
    *,
    calls: int,
    forms: int,
    conversion_rate: Decimal,
    average_ticket: Decimal,
    pos_revenue: Decimal,
) -> tuple[Decimal, bool]:
    """Return (revenue, using_pos). POS wins when > 0 for that day."""
    if pos_revenue and pos_revenue > 0:
        return pos_revenue, True
    leads = Decimal(calls + forms)
    return leads * conversion_rate * average_ticket, False


async def summarize_roi(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    days: int = 30,
) -> tuple[dict, list[dict]]:
    client = (
        await db.execute(select(Client).where(Client.client_id == client_id))
    ).scalar_one()
    end = date.today()
    start = end - timedelta(days=max(days - 1, 0))

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

    conversion = client.conversion_rate_estimate or Decimal("0.25")
    ticket = client.average_ticket_value or Decimal("150.00")

    total_calls = 0
    total_forms = 0
    total_reviews = 0
    total_ad = Decimal(0)
    total_pos = Decimal(0)
    total_est = Decimal(0)
    any_pos = False
    breakdown: list[dict] = []

    for row in rows:
        day_rev, used_pos = estimate_day_revenue(
            calls=row.tracked_calls_count or 0,
            forms=row.form_leads_count or 0,
            conversion_rate=conversion,
            average_ticket=ticket,
            pos_revenue=row.pos_attributed_revenue_usd or Decimal(0),
        )
        if used_pos:
            any_pos = True
        total_calls += row.tracked_calls_count or 0
        total_forms += row.form_leads_count or 0
        total_reviews += row.new_reviews_count or 0
        total_ad += row.ad_spend_usd or Decimal(0)
        total_pos += row.pos_attributed_revenue_usd or Decimal(0)
        total_est += day_rev
        breakdown.append(
            {
                "metric_date": row.metric_date.isoformat(),
                "tracked_calls_count": row.tracked_calls_count or 0,
                "form_leads_count": row.form_leads_count or 0,
                "gbp_direction_requests": row.gbp_direction_requests or 0,
                "new_reviews_count": row.new_reviews_count or 0,
                "ad_spend_usd": float(row.ad_spend_usd or 0),
                "pos_attributed_revenue_usd": float(row.pos_attributed_revenue_usd or 0),
                "estimated_revenue_usd": float(day_rev),
            }
        )

    if not any_pos:
        # Period-level estimate from totals (same formula as PRD)
        total_est = Decimal(total_calls + total_forms) * conversion * ticket

    summary = {
        "client_id": client_id,
        "days": days,
        "total_calls": total_calls,
        "total_form_leads": total_forms,
        "total_leads": total_calls + total_forms,
        "total_reviews": total_reviews,
        "total_ad_spend_usd": float(total_ad),
        "total_pos_revenue_usd": float(total_pos),
        "estimated_revenue_usd": float(total_est if not any_pos else total_pos),
        "using_pos": any_pos,
        "average_ticket_value": float(ticket),
        "conversion_rate_estimate": float(conversion),
    }
    return summary, breakdown
