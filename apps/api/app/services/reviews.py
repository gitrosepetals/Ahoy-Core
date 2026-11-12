"""Reputation Radar (CL-05): draft, schedule, approve and post review replies; provider sync."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Client, DailyRoiMetric, ReplyStatus, Review, ReviewProvider
from app.services import review_providers as rp
from app.services.brand_context import load_brand_context
from app.services.credentials import get_credential
from app.services.llm import draft_review_reply
from app.services.notify import notify_captain_low_star_review

logger = logging.getLogger(__name__)

MAX_REPLY_ATTEMPTS = 3


def needs_captain(review: Review) -> bool:
    return (review.rating or 0) <= 3 and review.reply_status == ReplyStatus.awaiting_captain


async def list_client_reviews(db: AsyncSession, client_id: uuid.UUID) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.client_id == client_id)
        .order_by(Review.reviewed_at.desc().nullslast(), Review.created_at.desc())
    )
    return list(result.scalars().all())


async def _delay_hours(db: AsyncSession, client_id: uuid.UUID) -> int:
    client = await db.get(Client, client_id)
    return client.auto_reply_delay_hours if client else 24


async def ensure_ai_reply(
    db: AsyncSession,
    settings: Settings,
    review: Review,
) -> Review:
    """Draft a reply once. 4-5★ → scheduled (posted after the client's delay); 1-3★ → Captain."""
    if review.ai_reply:
        await flag_low_star_if_needed(db, settings, review)
        return review
    brand = await load_brand_context(db, review.client_id)
    reply, meta = await draft_review_reply(
        settings,
        brand=brand,
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
        review.reply_status = ReplyStatus.scheduled
        review.reply_due_at = datetime.now(UTC) + timedelta(
            hours=await _delay_hours(db, review.client_id)
        )
    await db.flush()
    await flag_low_star_if_needed(db, settings, review)
    return review


async def post_review_reply(db: AsyncSession, settings: Settings, review: Review) -> bool:
    """Post ``review.ai_reply`` to the provider. Returns True when posted (or dev-posted)."""
    if review.reply_posted_at is not None:
        return True
    text = (review.ai_reply or "").strip()
    if not text:
        return False
    meta = dict(review.generation_meta or {})
    try:
        if not rp.provider_can_reply(review.provider):
            raise rp.ProviderError(f"{review.provider.value} has no reply API — post it by hand")
        client = await db.get(Client, review.client_id)
        creds = await get_credential(db, settings, review.client_id, review.provider.value) or {}
        if review.provider == ReviewProvider.google and creds.get("refresh_token"):
            token = await rp.google_access_token(settings, creds["refresh_token"])
            await rp.google_reply(token, client.gbp_location_id, review.external_id, text)
            meta["posted_via"] = "google"
        elif review.provider == ReviewProvider.facebook and creds.get("page_access_token"):
            if not review.reply_target:
                raise rp.ProviderError("Facebook review has no story id to reply to")
            await rp.facebook_reply(creds["page_access_token"], review.reply_target, text)
            meta["posted_via"] = "facebook"
        elif settings.environment == "development":
            meta["posted_via"] = "dev"  # not connected locally: pretend, so the flow completes
        else:
            raise rp.ProviderError(f"{review.provider.value} is not connected for this client")
    except rp.ProviderError as exc:
        meta["reply_attempts"] = int(meta.get("reply_attempts", 0)) + 1
        if not rp.provider_can_reply(review.provider):
            meta["needs_manual_reply"] = True
        review.reply_error = str(exc)[:500]
        review.generation_meta = meta
        await db.flush()
        logger.warning("Review reply failed for %s: %s", review.review_id, exc)
        return False

    review.reply_posted_at = datetime.now(UTC)
    review.reply_error = None
    if review.reply_status == ReplyStatus.scheduled:
        review.reply_status = ReplyStatus.auto_sent
    review.generation_meta = meta
    await db.flush()
    return True


async def approve_review_reply(
    db: AsyncSession,
    settings: Settings,
    review: Review,
    *,
    reply_text: str | None = None,
) -> Review:
    """Captain one-click approve (optionally edited) — posts immediately; the worker retries."""
    review = await ensure_ai_reply(db, settings, review)
    if reply_text and reply_text.strip():
        review.ai_reply = reply_text.strip()
    review.reply_status = ReplyStatus.captain_approved
    review.reply_due_at = datetime.now(UTC)
    await db.flush()
    await post_review_reply(db, settings, review)
    return review


async def skip_review_reply(db: AsyncSession, review: Review) -> Review:
    review.reply_status = ReplyStatus.skipped
    review.reply_due_at = None
    await db.flush()
    return review


async def post_due_review_replies(
    db: AsyncSession, settings: Settings, *, now: datetime | None = None
) -> dict:
    """Worker job: post scheduled 4-5★ replies whose delay passed + approved ones that failed."""
    now = now or datetime.now(UTC)
    reviews = (
        await db.execute(
            select(Review)
            .where(
                Review.reply_posted_at.is_(None),
                Review.reply_due_at <= now,
                or_(
                    Review.reply_status == ReplyStatus.scheduled,
                    Review.reply_status == ReplyStatus.captain_approved,
                ),
            )
            .limit(50)
        )
    ).scalars().all()
    posted = failed = 0
    for review in reviews:
        meta = review.generation_meta or {}
        if meta.get("needs_manual_reply") or int(meta.get("reply_attempts", 0)) >= MAX_REPLY_ATTEMPTS:
            continue
        if await post_review_reply(db, settings, review):
            posted += 1
        else:
            failed += 1
    return {"posted": posted, "failed": failed}


async def _client_creds(db: AsyncSession, settings: Settings, client: Client) -> dict[str, dict]:
    out = {}
    for provider in ("google", "facebook"):
        cred = await get_credential(db, settings, client.client_id, provider)
        if cred:
            out[provider] = cred
    return out


async def sync_client_reviews(db: AsyncSession, settings: Settings, client: Client) -> dict:
    """Pull recent reviews from every connected provider; draft + schedule/alert new ones."""
    creds = await _client_creds(db, settings, client)
    stats = {"new": 0, "errors": []}
    for provider in rp.configured_providers(client, settings, creds):
        try:
            if provider == "google":
                token = await rp.google_access_token(settings, creds["google"]["refresh_token"])
                fetched = await rp.google_fetch_reviews(token, client.gbp_location_id)
            elif provider == "facebook":
                fetched = await rp.facebook_fetch_reviews(
                    client.facebook_page_id, creds["facebook"]["page_access_token"]
                )
            else:
                fetched = await rp.yelp_fetch_reviews(settings.yelp_api_key, client.yelp_business_id)
        except rp.ProviderError as exc:
            stats["errors"].append(f"{provider}: {exc}")
            continue
        stats["new"] += await ingest_reviews(db, settings, client, ReviewProvider(provider), fetched)
    return stats


async def ingest_reviews(
    db: AsyncSession,
    settings: Settings,
    client: Client,
    provider: ReviewProvider,
    fetched: list[rp.FetchedReview],
) -> int:
    """Upsert fetched reviews; returns how many were new. Shared by sync + tests."""
    new = 0
    for f in fetched:
        existing = (
            await db.execute(
                select(Review).where(
                    Review.client_id == client.client_id,
                    Review.provider == provider,
                    Review.external_id == f.external_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.body = f.body
            existing.rating = f.rating
            continue
        review = Review(
            client_id=client.client_id,
            provider=provider,
            external_id=f.external_id,
            rating=f.rating,
            body=f.body,
            reviewer_name=f.reviewer_name,
            reviewed_at=f.reviewed_at or datetime.now(UTC),
            reply_target=f.reply_target,
        )
        if f.existing_reply:
            # Owner already answered on the platform — record it, don't double-reply
            review.ai_reply = f.existing_reply
            review.reply_status = ReplyStatus.skipped
            review.reply_posted_at = review.reviewed_at
            review.generation_meta = {"existing_reply": True}
        db.add(review)
        await db.flush()
        if not f.existing_reply:
            await ensure_ai_reply(db, settings, review)
        new += 1
    return new


async def sync_all_reviews(db: AsyncSession, settings: Settings) -> dict:
    clients = (await db.execute(select(Client))).scalars().all()
    totals = {"clients": 0, "new": 0, "errors": []}
    for client in clients:
        stats = await sync_client_reviews(db, settings, client)
        if stats["new"] or stats["errors"]:
            totals["clients"] += 1
        totals["new"] += stats["new"]
        totals["errors"] += stats["errors"]
    return totals


async def sync_gbp_performance(db: AsyncSession, settings: Settings, *, days: int = 10) -> dict:
    """Worker job: GBP impressions / clicks / direction requests → daily_roi_metrics.

    Google reports with a few days' lag, so the last ``days`` days are refreshed each run.
    """
    clients = (
        await db.execute(select(Client).where(Client.gbp_location_id.is_not(None)))
    ).scalars().all()
    updated = 0
    for client in clients:
        creds = await get_credential(db, settings, client.client_id, "google")
        if not creds or not creds.get("refresh_token"):
            continue
        today = datetime.now(ZoneInfo(client.timezone or "America/Chicago")).date()
        try:
            token = await rp.google_access_token(settings, creds["refresh_token"])
            series = await rp.google_fetch_performance(
                token, client.gbp_location_id, today - timedelta(days=days), today
            )
        except rp.ProviderError as exc:
            logger.warning("GBP performance failed for %s: %s", client.business_name, exc)
            continue
        updated += await upsert_performance(db, client.client_id, series)
    return {"days_updated": updated}


async def upsert_performance(
    db: AsyncSession, client_id: uuid.UUID, series: dict[date, dict[str, int]]
) -> int:
    for d, values in series.items():
        stmt = insert(DailyRoiMetric).values(client_id=client_id, metric_date=d, **values)
        await db.execute(
            stmt.on_conflict_do_update(index_elements=["client_id", "metric_date"], set_=values)
        )
    await db.flush()
    return len(series)


async def flag_low_star_if_needed(
    db: AsyncSession,
    settings: Settings,
    review: Review,
) -> dict | None:
    """CL-05: alert the Captain once per new 1-3★ review that is waiting on them."""
    if review.rating > 3 or review.alerted_at is not None:
        return None
    if review.reply_status != ReplyStatus.awaiting_captain:
        return None
    result = await notify_captain_low_star_review(
        db,
        settings,
        client_id=review.client_id,
        rating=review.rating,
        review_id=review.review_id,
        reviewer_name=review.reviewer_name,
        draft_reply=review.ai_reply,
    )
    review.alerted_at = datetime.now(UTC)
    await db.flush()
    return result
