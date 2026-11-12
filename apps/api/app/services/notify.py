"""Captain notifications: push first (FCM), SMS with a 48h magic link as fallback, log in dev.

Every attempt is recorded in ``notifications`` (delivery audit + PRD §7 engagement KPIs).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Client, DevicePushToken, Notification, User
from app.services.auth import create_magic_link
from app.services.push import PushTokenInvalid, push_enabled, send_push
from app.services.sms import send_sms, sms_enabled

logger = logging.getLogger(__name__)

QUEUE_DEEP_LINK = "/ship/posts?tab=pending"
REVIEWS_DEEP_LINK = "/ship/reviews"


async def _notify_owner(
    db: AsyncSession,
    settings: Settings,
    *,
    client: Client,
    kind: str,
    title: str,
    body: str,
    deep_link: str,
    data: dict[str, str] | None = None,
) -> Notification:
    owner = (
        await db.execute(select(User).where(User.user_id == client.owner_user_id))
    ).scalar_one_or_none()
    tokens = (
        await db.execute(
            select(DevicePushToken).where(
                DevicePushToken.user_id == client.owner_user_id,
                DevicePushToken.enabled.is_(True),
            )
        )
    ).scalars().all()

    payload: dict = {
        "business_name": client.business_name,
        "push_token_count": len(tokens),
        **(data or {}),
    }
    note = Notification(
        client_id=client.client_id,
        user_id=owner.user_id if owner else None,
        kind=kind,
        deep_link=deep_link,
        body=body,
        payload=payload,
    )

    # 1) Push to every live device
    if tokens and push_enabled(settings):
        sent, errors = 0, []
        for t in tokens:
            try:
                await send_push(
                    settings,
                    token=t.token,
                    title=title,
                    body=body,
                    data={"path": deep_link, "kind": kind, **(data or {})},
                )
                sent += 1
            except PushTokenInvalid:
                t.enabled = False
            except Exception as exc:
                errors.append(str(exc))
        if sent:
            note.channel, note.status = "push", "sent"
            payload["push_sent"] = sent
            db.add(note)
            await db.flush()
            return note
        logger.warning("Push failed for %s (%s); falling back to SMS", client.business_name, errors)
        payload["push_errors"] = errors

    # 2) SMS with a single-use magic link that signs the Captain in and opens the deep link
    phone = owner.phone_number if owner else None
    link_url = None
    if owner:
        link_url, _ = await create_magic_link(
            db,
            user=owner,
            redirect_path=deep_link,
            settings=settings,
            ttl=timedelta(hours=settings.notify_link_ttl_hours),
        )
    text = f"{body} {link_url}" if link_url else body

    if phone and sms_enabled(settings):
        try:
            payload["sms_sid"] = await send_sms(settings, to=phone, body=text)
            note.channel, note.status = "sms", "sent"
        except Exception as exc:
            logger.exception("SMS notification failed")
            note.channel, note.status, note.error = "sms", "failed", str(exc)
    else:
        logger.info("NOTIFY (dev log) %s → %s: %s", kind, phone or "no phone", text)
        note.channel, note.status = "log", "logged"
        payload["dev_magic_link"] = link_url

    note.body = text
    db.add(note)
    await db.flush()
    return note


def notification_summary(note: Notification) -> dict:
    """Compact dict stored on posts (``generation_meta.last_notify``) for Crew visibility."""
    return {
        "notification_id": str(note.notification_id),
        "type": note.kind,
        "channel": note.channel,
        "status": note.status,
        "deep_link": note.deep_link,
        "at": datetime.now(UTC).isoformat(),
    }


async def _client(db: AsyncSession, client_id: uuid.UUID) -> Client | None:
    return (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one_or_none()


async def notify_captain_queue_ready(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    post_count: int,
) -> dict:
    client = await _client(db, client_id)
    if client is None:
        return {"ok": False, "reason": "client_not_found"}
    note = await _notify_owner(
        db,
        settings,
        client=client,
        kind="queue_ready",
        title="Ahoy, Captain — posts ready",
        body=f"Ahoy, Captain! {post_count} new post{'s' if post_count != 1 else ''} for "
        f"{client.business_name} are on your Manifest awaiting your mark.",
        deep_link=QUEUE_DEEP_LINK,
        data={"post_count": str(post_count)},
    )
    return {"ok": note.status != "failed", **notification_summary(note)}


async def notify_captain_queue_expiring(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    post_count: int,
    first_deadline: datetime,
) -> dict:
    client = await _client(db, client_id)
    if client is None:
        return {"ok": False, "reason": "client_not_found"}
    when = first_deadline.strftime("%a %b %d")
    note = await _notify_owner(
        db,
        settings,
        client=client,
        kind="queue_expiring",
        title="Posts awaiting the Captain",
        body=f"Captain, {post_count} post{'s' if post_count != 1 else ''} for "
        f"{client.business_name} need your mark before {when} or they stay in port.",
        deep_link=QUEUE_DEEP_LINK,
        data={"post_count": str(post_count)},
    )
    return {"ok": note.status != "failed", **notification_summary(note)}


async def notify_captain_low_star_review(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    rating: int,
    review_id: uuid.UUID,
    reviewer_name: str | None = None,
    draft_reply: str | None = None,
) -> dict:
    client = await _client(db, client_id)
    if client is None:
        return {"ok": False, "reason": "client_not_found"}
    who = reviewer_name or "A customer"
    snippet = f' Draft reply ready: "{draft_reply[:90]}…"' if draft_reply else ""
    note = await _notify_owner(
        db,
        settings,
        client=client,
        kind="low_star_review",
        title=f"Storm on the Radar: {rating}★ review",
        body=f"Captain, {who} left {client.business_name} a {rating}★ review.{snippet} Tap to approve:",
        deep_link=REVIEWS_DEEP_LINK,
        data={"review_id": str(review_id), "rating": str(rating)},
    )
    return {"ok": note.status != "failed", **notification_summary(note)}
