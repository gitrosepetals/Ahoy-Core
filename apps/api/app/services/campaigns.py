from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    ApprovalStatus,
    BrandProfile,
    ContentQueue,
    MediaAsset,
    PlatformChannel,
)
from app.services.llm import generate_caption, revise_caption


async def generate_campaign_posts(
    db: AsyncSession,
    settings: Settings,
    *,
    client_id: uuid.UUID,
    asset_ids: list[uuid.UUID],
    channels: list[PlatformChannel],
    days: int,
    count: int,
) -> list[ContentQueue]:
    brand = (
        await db.execute(select(BrandProfile).where(BrandProfile.client_id == client_id))
    ).scalar_one_or_none()
    voice = brand.brand_voice_guidelines if brand else "Warm, professional, community-focused."
    compliance = brand.compliance_rules if brand else None
    services = brand.services_offered if brand else None

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

    now = datetime.now(UTC)
    spacing = max(days / max(count, 1), 0.25)
    posts: list[ContentQueue] = []

    for i in range(count):
        channel = channels[i % len(channels)]
        asset = assets[i % len(assets)] if assets else None
        caption, meta = await generate_caption(
            settings,
            brand_voice=voice,
            compliance=compliance,
            services=services,
            channel=channel.value,
            asset_tags=asset.ai_tags if asset else None,
            asset_notes=(asset.transcript or asset.storage_url) if asset else "text-only",
            index=i,
        )
        scheduled = now + timedelta(days=spacing * (i + 1))
        post = ContentQueue(
            client_id=client_id,
            asset_id=asset.asset_id if asset else None,
            channel=channel,
            caption_text=caption,
            scheduled_publish_at=scheduled,
            status=ApprovalStatus.draft_internal,
            generation_meta={**meta, "batch_index": i, "days": days, "count": count},
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
    brand = (
        await db.execute(select(BrandProfile).where(BrandProfile.client_id == post.client_id))
    ).scalar_one_or_none()
    voice = brand.brand_voice_guidelines if brand else "Warm, professional, community-focused."
    compliance = brand.compliance_rules if brand else None

    revised, meta = await revise_caption(
        settings,
        brand_voice=voice,
        compliance=compliance,
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
