from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import BrandProfile, Client
from app.services.llm import embed_text

DEFAULT_VOICE = "Warm, professional, community-focused."


@dataclass
class BrandContext:
    """Everything the Brand Brain knows about a client, injected into every LLM prompt (AG-01)."""

    business_name: str = ""
    industry: str = ""
    voice: str = DEFAULT_VOICE
    compliance: str | None = None
    services: object = None
    pricing: str | None = None
    seasonal_offers: object = None
    zips: list[str] = field(default_factory=list)
    seo_keywords: list[str] = field(default_factory=list)

    def as_prompt(self) -> str:
        def _json(value: object) -> str:
            return json.dumps(value) if value not in (None, {}, []) else "(none)"

        return "\n".join(
            [
                f"Business: {self.business_name or '(unknown)'} ({self.industry or 'local business'})",
                f"Brand voice:\n{self.voice}",
                f"Compliance (must follow):\n{self.compliance or '(none)'}",
                f"Services / menu: {_json(self.services)}",
                f"Pricing: {self.pricing or '(none)'}",
                f"Seasonal offers: {_json(self.seasonal_offers)}",
                f"Target ZIP codes: {', '.join(self.zips) or '(none)'}",
                f"Local SEO keywords: {', '.join(self.seo_keywords) or '(none)'}",
            ]
        )


def brand_text_for_embedding(profile: BrandProfile) -> str:
    return BrandContext(
        voice=profile.brand_voice_guidelines,
        compliance=profile.compliance_rules,
        services=profile.services_offered,
        pricing=profile.pricing_notes,
        seasonal_offers=profile.seasonal_offers,
        zips=list(profile.target_zip_codes or []),
        seo_keywords=list(profile.local_seo_keywords or []),
    ).as_prompt()


async def load_brand_context(db: AsyncSession, client_id: uuid.UUID) -> BrandContext:
    client = (
        await db.execute(select(Client).where(Client.client_id == client_id))
    ).scalar_one_or_none()
    profile = (
        await db.execute(select(BrandProfile).where(BrandProfile.client_id == client_id))
    ).scalar_one_or_none()
    ctx = BrandContext(
        business_name=client.business_name if client else "",
        industry=client.industry_vertical if client else "",
    )
    if profile:
        ctx.voice = profile.brand_voice_guidelines or DEFAULT_VOICE
        ctx.compliance = profile.compliance_rules
        ctx.services = profile.services_offered
        ctx.pricing = profile.pricing_notes
        ctx.seasonal_offers = profile.seasonal_offers
        ctx.zips = list(profile.target_zip_codes or [])
        ctx.seo_keywords = list(profile.local_seo_keywords or [])
    return ctx


async def get_or_create_brand_profile(db: AsyncSession, client_id: uuid.UUID) -> BrandProfile:
    result = await db.execute(select(BrandProfile).where(BrandProfile.client_id == client_id))
    profile = result.scalar_one_or_none()
    if profile:
        return profile
    profile = BrandProfile(
        client_id=client_id,
        brand_voice_guidelines=DEFAULT_VOICE,
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
    profile.context_embedding = await embed_text(settings, brand_text_for_embedding(profile))
