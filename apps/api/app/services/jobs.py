"""Periodic jobs. Pure functions over a session so tests (and the scheduler) can call them."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import ApprovalStatus, ContentQueue
from app.services.notify import notify_captain_queue_expiring

logger = logging.getLogger(__name__)

AWAITING_CAPTAIN = (ApprovalStatus.pending_client, ApprovalStatus.changes_requested)
# Don't send a "reminder" right on the heels of the queue-ready message.
REMINDER_QUIET_AFTER_RELEASE = timedelta(hours=1)


async def expire_overdue_posts(db: AsyncSession, *, now: datetime | None = None) -> int:
    """Posts never approved by their publish time can't go out → ``expired`` (back to Crew)."""
    now = now or datetime.now(UTC)
    posts = (
        await db.execute(
            select(ContentQueue).where(
                ContentQueue.status.in_(AWAITING_CAPTAIN),
                ContentQueue.scheduled_publish_at <= now,
            )
        )
    ).scalars().all()
    for post in posts:
        post.status = ApprovalStatus.expired
        meta = dict(post.generation_meta or {})
        meta["expired_at"] = now.isoformat()
        post.generation_meta = meta
    await db.flush()
    if posts:
        logger.info("Expired %d unapproved posts", len(posts))
    return len(posts)


async def send_expiry_reminders(
    db: AsyncSession,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> list[dict]:
    """CL-02: one reminder per client when posts awaiting the Captain expire within 48h."""
    now = now or datetime.now(UTC)
    horizon = now + timedelta(hours=settings.queue_reminder_hours_before)
    posts = (
        await db.execute(
            select(ContentQueue).where(
                ContentQueue.status == ApprovalStatus.pending_client,
                ContentQueue.reminder_sent_at.is_(None),
                ContentQueue.scheduled_publish_at > now,
                ContentQueue.scheduled_publish_at <= horizon,
            )
        )
    ).scalars().all()

    by_client: dict[uuid.UUID, list[ContentQueue]] = defaultdict(list)
    for post in posts:
        if post.released_at and post.released_at > now - REMINDER_QUIET_AFTER_RELEASE:
            continue
        by_client[post.client_id].append(post)

    results: list[dict] = []
    for client_id, client_posts in by_client.items():
        first = min(p.scheduled_publish_at for p in client_posts)
        result = await notify_captain_queue_expiring(
            db,
            settings,
            client_id=client_id,
            post_count=len(client_posts),
            first_deadline=first,
        )
        for post in client_posts:
            post.reminder_sent_at = now
        results.append({"client_id": str(client_id), "posts": len(client_posts), **result})
    await db.flush()
    return results
