from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import BrandProfile, ReplyStatus, Review
from app.services.llm import draft_review_reply
from app.services.notify import notify_captain_low_star_review


def needs_captain(review: Review) -> bool:
    return (review.rating or 0) <= 3 and review.reply_status == ReplyStatus.awaiting_captain


async def list_client_reviews(db: AsyncSession, client_id: uuid.UUID) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.client_id == client_id)
        .order_by(Review.reviewed_at.desc().nullslast(), Review.created_at.desc())
    )
    return list(result.scalars().all())


async def ensure_ai_reply(
    db: AsyncSession,
    settings: Settings,
    review: Review,
) -> Review:
    if review.ai_reply:
        return review
    brand = (
        await db.execute(select(BrandProfile).where(BrandProfile.client_id == review.client_id))
    ).scalar_one_or_none()
    voice = brand.brand_voice_guidelines if brand else "Warm, professional, community-focused."
    reply, meta = await draft_review_reply(
        settings,
        brand_voice=voice,
        rating=review.rating,
        body=review.body or "",
        reviewer_name=review.reviewer_name or "there",
    )
    review.ai_reply = reply
    prev = dict(review.generation_meta or {})
    prev["draft"] = meta
    review.generation_meta = prev
    if review.rating <= 3 and not review.reply_status:
        review.reply_status = ReplyStatus.awaiting_captain
    elif review.rating >= 4 and not review.reply_status:
        review.reply_status = ReplyStatus.auto_sent
    await db.flush()
    return review


async def approve_review_reply(
    db: AsyncSession,
    settings: Settings,
    review: Review,
) -> Review:
    review = await ensure_ai_reply(db, settings, review)
    review.reply_status = ReplyStatus.captain_approved
    await db.flush()
    return review


async def flag_low_star_if_needed(
    db: AsyncSession,
    settings: Settings,
    review: Review,
) -> dict | None:
    if review.rating > 3:
        return None
    return await notify_captain_low_star_review(
        db,
        settings,
        client_id=review.client_id,
        rating=review.rating,
        review_id=review.review_id,
    )
