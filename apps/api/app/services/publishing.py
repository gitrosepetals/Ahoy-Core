"""CL-02 auto-publish: approved posts go out at ``scheduled_publish_at`` via Ayrshare.

Ayrshare (Business plan) fans one API call out to Instagram / Facebook / TikTok / Google
Business Profile using the client's Ayrshare **profile key** (stored encrypted, provider
``ayrshare``). Email and SMS are not Ayrshare channels: those posts are flagged for Crew to
send manually until an email/SMS provider is wired.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import ApprovalStatus, ContentQueue, MediaAsset, PlatformChannel
from app.services.credentials import get_credential

logger = logging.getLogger(__name__)

AYRSHARE_URL = "https://api.ayrshare.com/api/post"
AYRSHARE_PLATFORMS: dict[PlatformChannel, str] = {
    PlatformChannel.instagram_post: "instagram",
    PlatformChannel.instagram_reel: "instagram",
    PlatformChannel.facebook: "facebook",
    PlatformChannel.tiktok: "tiktok",
    PlatformChannel.gbp_update: "gmb",
}
MANUAL_CHANNELS = {PlatformChannel.email_blast, PlatformChannel.sms_promo}
BATCH_LIMIT = 50


class PublishError(Exception):
    pass


def publish_live(settings: Settings) -> bool:
    return bool(settings.ayrshare_api_key)


def build_ayrshare_body(post: ContentQueue, media_url: str | None) -> dict:
    body: dict = {"post": post.caption_text, "platforms": [AYRSHARE_PLATFORMS[post.channel]]}
    if media_url:
        body["mediaUrls"] = [media_url]
    if post.channel == PlatformChannel.instagram_reel:
        body["instagramOptions"] = {"reels": True, "shareReelsFeed": True}
    if post.channel == PlatformChannel.gbp_update:
        body["gmbOptions"] = {"callToAction": {"actionType": "call"}}
    return body


async def _ayrshare_post(settings: Settings, *, profile_key: str | None, body: dict) -> str:
    headers = {"Authorization": f"Bearer {settings.ayrshare_api_key}"}
    if profile_key:
        headers["Profile-Key"] = profile_key
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(AYRSHARE_URL, headers=headers, json=body)
    data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
    if res.status_code >= 400 or data.get("status") == "error":
        raise PublishError(f"Ayrshare {res.status_code}: {str(data or res.text)[:300]}")
    return str(data.get("id") or "")


async def publish_post(db: AsyncSession, settings: Settings, post: ContentQueue) -> str:
    """Publish one post now. Returns the external id. Raises PublishError."""
    if post.channel in MANUAL_CHANNELS:
        raise PublishError(f"{post.channel.value} is not an Ayrshare channel; send manually")

    media_url = None
    if post.asset_id:
        asset = (
            await db.execute(select(MediaAsset).where(MediaAsset.asset_id == post.asset_id))
        ).scalar_one_or_none()
        media_url = asset.storage_url if asset else None
    if post.channel == PlatformChannel.tiktok and not media_url:
        raise PublishError("TikTok requires a video/photo asset")

    if not publish_live(settings):
        return f"dev-{uuid.uuid4()}"

    creds = await get_credential(db, settings, post.client_id, "ayrshare")
    profile_key = (creds or {}).get("profile_key")
    if not profile_key:
        raise PublishError("Client has no Ayrshare profile key (Crew → Integrations)")
    return await _ayrshare_post(
        settings, profile_key=profile_key, body=build_ayrshare_body(post, media_url)
    )


async def publish_due_posts(
    db: AsyncSession, settings: Settings, *, now: datetime | None = None
) -> dict:
    now = now or datetime.now(UTC)
    posts = (
        await db.execute(
            select(ContentQueue)
            .where(
                ContentQueue.status == ApprovalStatus.approved,
                ContentQueue.scheduled_publish_at <= now,
            )
            .order_by(ContentQueue.scheduled_publish_at.asc())
            .limit(BATCH_LIMIT)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()

    published = failed = skipped = 0
    for post in posts:
        meta = dict(post.generation_meta or {})
        if meta.get("publish_failed") or meta.get("needs_manual_publish"):
            skipped += 1
            continue
        try:
            external_id = await publish_post(db, settings, post)
        except PublishError as exc:
            attempts = int(meta.get("publish_attempts", 0)) + 1
            meta["publish_attempts"] = attempts
            meta["publish_error"] = str(exc)
            if post.channel in MANUAL_CHANNELS:
                meta["needs_manual_publish"] = True
            elif attempts >= settings.publish_max_attempts:
                meta["publish_failed"] = True
            post.generation_meta = meta
            failed += 1
            logger.warning("Publish failed for post %s: %s", post.post_id, exc)
            continue
        post.status = ApprovalStatus.published
        post.published_external_id = external_id[:150]
        meta["published_at"] = now.isoformat()
        meta.pop("publish_error", None)
        post.generation_meta = meta
        published += 1

    await db.flush()
    return {"published": published, "failed": failed, "skipped": skipped}
