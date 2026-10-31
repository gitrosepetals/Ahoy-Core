from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import BrandProfile
from app.services.llm import embed_text


def brand_text_for_embedding(
    *,
    voice: str,
    compliance: str | None,
    services: object,
    zips: list[str] | None,
) -> str:
    parts = [
        f"Voice: {voice}",
        f"Compliance: {compliance or ''}",
        f"Services: {json.dumps(services) if services is not None else ''}",
        f"Zips: {', '.join(zips or [])}",
    ]
    return "\n".join(parts)


async def get_or_create_brand_profile(db: AsyncSession, client_id: uuid.UUID) -> BrandProfile:
    result = await db.execute(select(BrandProfile).where(BrandProfile.client_id == client_id))
    profile = result.scalar_one_or_none()
    if profile:
        return profile
    profile = BrandProfile(
        client_id=client_id,
        brand_voice_guidelines="Warm, professional, community-focused.",
        target_zip_codes=[],
        compliance_rules="",
        services_offered={},
    )
    db.add(profile)
    await db.flush()
    return profile


async def recompute_embedding(settings: Settings, profile: BrandProfile) -> None:
    """Recompute context_embedding when LLM key present or LLM_DEV_MODE (always for local)."""
    if not settings.llm_dev_mode and not settings.openai_api_key:
        return
    text = brand_text_for_embedding(
        voice=profile.brand_voice_guidelines,
        compliance=profile.compliance_rules,
        services=profile.services_offered,
        zips=profile.target_zip_codes,
    )
    profile.context_embedding = await embed_text(settings, text)
