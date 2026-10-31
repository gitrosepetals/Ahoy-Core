"""Notify stub: look up push tokens; SMS only if Twilio configured; otherwise log."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Client, DevicePushToken, User

logger = logging.getLogger(__name__)


async def notify_captain_queue_ready(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    post_count: int,
) -> dict:
    result = await db.execute(select(Client).where(Client.client_id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        return {"ok": False, "reason": "client_not_found"}

    owner_id = client.owner_user_id
    tokens = (
        await db.execute(
            select(DevicePushToken).where(
                DevicePushToken.user_id == owner_id,
                DevicePushToken.enabled.is_(True),
            )
        )
    ).scalars().all()

    intent = {
        "type": "queue_ready",
        "client_id": str(client_id),
        "business_name": client.business_name,
        "post_count": post_count,
        "deep_link": "/ship/posts?tab=pending",
        "push_token_count": len(tokens),
        "push_platforms": [t.platform.value for t in tokens],
    }

    if tokens:
        logger.info("NOTIFY_STUB push intent: %s", intent)
        return {"ok": True, "channel": "push_stub", **intent}

    owner = (
        await db.execute(select(User).where(User.user_id == owner_id))
    ).scalar_one_or_none()
    phone = owner.phone_number if owner else None

    twilio_ready = bool(
        settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number
    )
    if phone and twilio_ready and not settings.auth_dev_mode:
        # Real SMS would go here in a later milestone; still stub for B.
        logger.info(
            "NOTIFY_STUB would SMS %s (Twilio configured): %s posts ready for %s",
            phone,
            post_count,
            client.business_name,
        )
        return {"ok": True, "channel": "sms_stub", "phone": phone, **intent}

    logger.info(
        "NOTIFY_STUB log-only (no push token%s): %s",
        "" if not phone else f"; captain phone={phone}",
        intent,
    )
    return {"ok": True, "channel": "log", **intent}


async def notify_captain_low_star_review(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    rating: int,
    review_id: uuid.UUID,
) -> dict:
    result = await db.execute(select(Client).where(Client.client_id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        return {"ok": False, "reason": "client_not_found"}

    owner_id = client.owner_user_id
    tokens = (
        await db.execute(
            select(DevicePushToken).where(
                DevicePushToken.user_id == owner_id,
                DevicePushToken.enabled.is_(True),
            )
        )
    ).scalars().all()

    intent = {
        "type": "low_star_review",
        "client_id": str(client_id),
        "business_name": client.business_name,
        "rating": rating,
        "review_id": str(review_id),
        "deep_link": "/ship/reviews",
        "push_token_count": len(tokens),
    }
    if tokens:
        logger.info("NOTIFY_STUB low-star push: %s", intent)
        return {"ok": True, "channel": "push_stub", **intent}

    logger.info("NOTIFY_STUB low-star log-only: %s", intent)
    return {"ok": True, "channel": "log", **intent}
