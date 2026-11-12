"""PRD §7 pilot KPIs, computed from data the platform already records.

- Client engagement: average time-to-approve (release → Captain approval), share under 48h
- Product stickiness: Captain active in the last 30 days (signed in or acted in the Ship)
- Business health: logo churn (canceled subscriptions / subscribed clients)
Operational efficiency (Crew minutes per client) and gross margin need time tracking /
cost data the platform doesn't hold — reported from outside the app.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent, Client, ContentQueue, Notification, Session

APPROVE_TARGET_HOURS = 48
WINDOW_DAYS = 30


async def client_kpis(db: AsyncSession, client: Client, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=WINDOW_DAYS)

    approvals = (
        await db.execute(
            select(ContentQueue.released_at, AuditEvent.created_at)
            .join(AuditEvent, AuditEvent.entity_id == cast(ContentQueue.post_id, String))
            .where(
                ContentQueue.client_id == client.client_id,
                ContentQueue.released_at.is_not(None),
                AuditEvent.entity_type == "post",
                AuditEvent.to_status == "approved",
                AuditEvent.actor_role == "captain",
                AuditEvent.created_at >= since,
            )
        )
    ).all()
    hours = [
        (approved - released).total_seconds() / 3600
        for released, approved in approvals
        if approved and released and approved >= released
    ]

    last_session = await db.scalar(
        select(func.max(Session.created_at)).where(Session.user_id == client.owner_user_id)
    )
    last_action = await db.scalar(
        select(func.max(AuditEvent.created_at)).where(
            AuditEvent.client_id == client.client_id, AuditEvent.actor_role == "captain"
        )
    )
    last_seen = max([t for t in (last_session, last_action) if t is not None], default=None)

    channels = dict(
        (
            await db.execute(
                select(Notification.channel, func.count())
                .where(Notification.client_id == client.client_id, Notification.created_at >= since)
                .group_by(Notification.channel)
            )
        ).all()
    )

    return {
        "client_id": client.client_id,
        "business_name": client.business_name,
        "approvals_30d": len(hours),
        "avg_time_to_approve_hours": round(sum(hours) / len(hours), 1) if hours else None,
        "approved_within_48h_pct": (
            round(100 * sum(h <= APPROVE_TARGET_HOURS for h in hours) / len(hours)) if hours else None
        ),
        "captain_active_30d": bool(last_seen and last_seen >= since),
        "captain_last_seen": last_seen,
        "notifications_30d": channels,
        "subscription_status": client.subscription_status,
    }


async def portfolio_kpis(db: AsyncSession, client_ids: list[uuid.UUID]) -> dict:
    clients = (
        (await db.execute(select(Client).where(Client.client_id.in_(client_ids)))).scalars().all()
        if client_ids
        else []
    )
    rows = [await client_kpis(db, c) for c in clients]
    timed = [r for r in rows if r["avg_time_to_approve_hours"] is not None]
    subscribed = [r for r in rows if r["subscription_status"] != "none"]
    canceled = [r for r in subscribed if r["subscription_status"] == "canceled"]
    return {
        "clients": rows,
        "summary": {
            "client_count": len(rows),
            "avg_time_to_approve_hours": (
                round(sum(r["avg_time_to_approve_hours"] for r in timed) / len(timed), 1) if timed else None
            ),
            "captain_active_30d_pct": round(100 * sum(r["captain_active_30d"] for r in rows) / len(rows))
            if rows
            else None,
            "logo_churn_pct": round(100 * len(canceled) / len(subscribed)) if subscribed else None,
            "targets": {
                "avg_time_to_approve_hours": f"< {APPROVE_TARGET_HOURS}",
                "captain_active_30d_pct": "> 85",
                "logo_churn_pct": "< 4 (monthly)",
            },
        },
    }
