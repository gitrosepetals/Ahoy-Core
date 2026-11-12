from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    ApprovalStatus,
    ContentQueue,
    MediaAsset,
    PlatformChannel,
)
from app.services.brand_context import load_brand_context
from app.services.llm import generate_caption, revise_caption

MAX_POSTS_PER_BATCH = 60


async def generate_campaign_posts(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    asset_ids: list[uuid.UUID],
    channels: list[PlatformChannel],
    days: int,
    count: int,
    fan_out: bool = False,
) -> list[ContentQueue]:
    """Create draft posts.

    Default: ``count`` posts, channels round-robin. With ``fan_out`` (AG-03 "single batch"),
    each of the ``count`` slots gets one formatted variation per channel, sharing asset + time.
    """
    brand = await load_brand_context(db, client_id)

    assets: list[MediaAsset] = []
    if asset_ids:
        result = await db.execute(
            select(MediaAsset).where(
                MediaAsset.client_id == client_id,
                MediaAsset.asset_id.in_(asset_ids),
            )
        )
        assets = list(result.scalars().all())
        if len(assets) != len(set(asset_ids)):
            missing = set(asset_ids) - {a.asset_id for a in assets}
            raise ValueError(f"Unknown or out-of-scope asset_ids: {sorted(str(m) for m in missing)}")

    if not channels:
        channels = [PlatformChannel.instagram_post]
    channels = list(dict.fromkeys(channels))
    if fan_out and count * len(channels) > MAX_POSTS_PER_BATCH:
        raise ValueError(
            f"Batch too large: {count} slots × {len(channels)} channels > {MAX_POSTS_PER_BATCH}"
        )

    now = datetime.now(UTC)
    spacing = max(days / max(count, 1), 0.25)
    batch_id = str(uuid.uuid4())
    posts: list[ContentQueue] = []

    for i in range(count):
        asset = assets[i % len(assets)] if assets else None
        slot_channels = channels if fan_out else [channels[i % len(channels)]]
        scheduled = now + timedelta(days=spacing * (i + 1))
        for channel in slot_channels:
            caption, meta = await generate_caption(
                settings,
                brand=brand,
                channel=channel.value,
                asset_tags=asset.ai_tags if asset else None,
                asset_notes=(asset.transcript or asset.storage_url) if asset else "text-only",
                index=i,
            )
            post = ContentQueue(
                client_id=client_id,
                asset_id=asset.asset_id if asset else None,
                channel=channel,
                caption_text=caption,
                scheduled_publish_at=scheduled,
                status=ApprovalStatus.draft_internal,
                generation_meta={
                    **meta,
                    "batch_id": batch_id,
                    "batch_index": i,
                    "days": days,
                    "count": count,
                    "fan_out": fan_out,
                },
            )
            db.add(post)
            posts.append(post)
        if asset:
            asset.is_used = True

    await db.flush()
    return posts


async def rewrite_post_from_feedback(
    db: AsyncSession,
    settings: Settings,
    post: ContentQueue,
    feedback: str,
) -> ContentQueue:
    brand = await load_brand_context(db, post.client_id)

    revised, meta = await revise_caption(
        settings,
        brand=brand,
        channel=post.channel.value,
        caption=post.caption_text,
        feedback=feedback,
    )
    post.client_feedback = feedback
    prev_meta = dict(post.generation_meta or {})
    prev_meta["revision"] = meta

    if revised is None:
        post.status = ApprovalStatus.changes_requested
        prev_meta["needs_crew"] = True
        post.generation_meta = prev_meta
    else:
        post.caption_text = revised
        post.status = ApprovalStatus.pending_client
        prev_meta["needs_crew"] = False
        post.generation_meta = prev_meta

    await db.flush()
    return post


def crew_edit_caption(
    post: ContentQueue,
    caption: str,
    *,
    scheduled_publish_at: datetime | None = None,
) -> ContentQueue:
    """Crew hand-edit (Story 1.2 fallback when the AI rewrite was flagged) or reschedule."""
    now = datetime.now(UTC)
    post.caption_text = caption
    meta = dict(post.generation_meta or {})
    meta["needs_crew"] = False
    meta["crew_edited_at"] = now.isoformat()
    post.generation_meta = meta
    if scheduled_publish_at is not None:
        post.scheduled_publish_at = scheduled_publish_at
    if post.status in (ApprovalStatus.changes_requested, ApprovalStatus.expired):
        post.status = ApprovalStatus.pending_client
        post.released_at = now
        post.reminder_sent_at = None
    return post
