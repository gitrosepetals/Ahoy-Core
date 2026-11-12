"""LLM helpers: OpenAI when configured, deterministic stub when LLM_DEV_MODE."""

from __future__ import annotations

import base64
import hashlib
import logging
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from app.config import Settings

if TYPE_CHECKING:
    from app.services.brand_context import BrandContext

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
EMBED_DIM = 1536

# AG-02 categories from the PRD; the tagger must pick from these (plus free-form extras).
ASSET_CATEGORIES = ("staff", "exterior", "interior", "product", "testimonial", "event")

# AG-03: per-channel output format. Hashtags only where the platform rewards them.
CHANNEL_RULES: dict[str, str] = {
    "instagram_post": (
        "Instagram feed post. 1-3 short paragraphs, emoji sparingly, end with a clear call to "
        "action. Then a blank line and 5-8 hashtags mixing local (city/neighborhood) and service tags."
    ),
    "instagram_reel": (
        "Instagram Reel caption. Hook in the first line (under 125 characters), 1-2 supporting "
        "lines, call to action, then 3-5 hashtags including one local tag."
    ),
    "tiktok": (
        "TikTok caption. Under 150 characters, punchy hook, then 3-5 hashtags including one local tag."
    ),
    "facebook": (
        "Facebook post. Conversational, 2-4 sentences, call to action to call or book. "
        "At most 2 hashtags."
    ),
    "gbp_update": (
        "Google Business Profile update. Plain text under 1500 characters, NO hashtags, no emoji. "
        "Lead with the service and the city/neighborhood (local SEO), end with a call to action "
        "such as 'Call us' or 'Book online'."
    ),
    "email_blast": (
        "Monthly email newsletter. First line 'Subject: ...', second line 'Preview: ...', then a "
        "120-200 word body with a greeting, 2-3 short sections and one call to action. No hashtags."
    ),
    "sms_promo": (
        "SMS promo under 160 characters including 'Reply STOP to opt out'. No hashtags, no emoji."
    ),
}
HASHTAG_CHANNELS = {"instagram_post", "instagram_reel", "tiktok", "facebook"}


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _live(settings: Settings) -> bool:
    return not settings.llm_dev_mode and bool(settings.openai_api_key)


async def _chat(
    settings: Settings,
    *,
    system: str,
    user: str | list[dict],
    temperature: float,
    timeout: float = 90.0,
) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_chat_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            },
        )
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()


def _dev_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals: list[float] = []
    seed = digest
    while len(vals) < EMBED_DIM:
        for b in seed:
            vals.append((b / 255.0) * 2 - 1)
            if len(vals) >= EMBED_DIM:
                break
        seed = hashlib.sha256(seed).digest()
    return vals


def _hashtag(text: str) -> str:
    return "#" + re.sub(r"[^A-Za-z0-9]", "", text.title())


def _dev_caption(*, channel: str, brand: BrandContext, asset_tags: list[str] | None, index: int) -> str:
    tags = ", ".join(asset_tags or ["general"])
    voice_snip = (brand.voice or "Friendly local tone").strip().split("\n")[0][:120]
    seo = brand.seo_keywords[0] if brand.seo_keywords else (brand.business_name or "our neighborhood")
    body = (
        f"[DEV] {channel.replace('_', ' ').title()} post {index + 1}: "
        f"Highlight {tags} for our community ({seo}). {voice_snip}"
    )
    if channel == "email_blast":
        return f"Subject: News from {brand.business_name or 'us'}\nPreview: {seo}\n\n{body}"
    if channel in HASHTAG_CHANNELS:
        hashtags = [_hashtag(brand.business_name or "Local")] + [
            _hashtag(k) for k in brand.seo_keywords[:2]
        ]
        return f"{body}\n\n{' '.join(hashtags)}"
    return body


def _dev_revise(caption: str, feedback: str) -> str:
    return f"[DEV revised] {caption}\n\n(Addressed: {feedback.strip()[:200]})"


def _dev_tags(filename: str) -> list[str]:
    name = filename.lower()
    hints = {
        "staff": ("staff", "team", "dr", "doctor", "portrait"),
        "exterior": ("exterior", "storefront", "outside", "sign", "building"),
        "interior": ("interior", "lobby", "office", "inside"),
        "product": ("product", "frame", "glasses", "menu", "item"),
        "testimonial": ("testimonial", "review", "interview", "qa"),
    }
    found = [cat for cat, words in hints.items() if any(w in name for w in words)]
    return found or ["uncategorized"]


async def embed_text(settings: Settings, text: str) -> list[float]:
    if not _live(settings):
        return _dev_embedding(text)
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.openai_embedding_model, "input": text},
        )
        res.raise_for_status()
        data = res.json()
        return list(data["data"][0]["embedding"])


async def generate_caption(
    settings: Settings,
    *,
    brand: BrandContext,
    channel: str,
    asset_tags: list[str] | None,
    asset_notes: str,
    index: int = 0,
) -> tuple[str, dict]:
    if not _live(settings):
        caption = _dev_caption(channel=channel, brand=brand, asset_tags=asset_tags, index=index)
        return caption, {"mode": "dev", "channel": channel, "index": index}

    prompt = _load_prompt("caption_batch.txt").format(
        brand_context=brand.as_prompt(),
        channel=channel,
        channel_rules=CHANNEL_RULES.get(channel, "Social post. Clear call to action."),
        asset_tags=", ".join(asset_tags or []) or "(none)",
        asset_notes=asset_notes or "(none)",
        today=date.today().isoformat(),
    )
    caption = await _chat(
        settings,
        system="You write compliant local-business marketing copy.",
        user=prompt,
        temperature=0.7,
    )
    return caption, {"mode": "openai", "model": settings.openai_chat_model, "channel": channel}


async def revise_caption(
    settings: Settings,
    *,
    brand: BrandContext,
    channel: str,
    caption: str,
    feedback: str,
) -> tuple[str | None, dict]:
    """Return (new_caption, meta). new_caption is None if rewrite should be flagged for Crew."""
    if not _live(settings):
        return _dev_revise(caption, feedback), {"mode": "dev", "action": "revise"}

    prompt = _load_prompt("caption_revision.txt").format(
        brand_context=brand.as_prompt(),
        channel=channel,
        channel_rules=CHANNEL_RULES.get(channel, "Social post. Clear call to action."),
        caption=caption,
        feedback=feedback,
    )
    try:
        revised = await _chat(
            settings,
            system="You revise captions from client feedback.",
            user=prompt,
            temperature=0.5,
        )
        if not revised:
            return None, {"mode": "openai", "action": "revise", "error": "empty_response"}
        return revised, {"mode": "openai", "model": settings.openai_chat_model, "action": "revise"}
    except Exception as exc:
        logger.exception("Caption revision failed")
        return None, {"mode": "openai", "action": "revise", "error": str(exc)}


async def draft_review_reply(
    settings: Settings,
    *,
    brand: BrandContext,
    rating: int,
    body: str,
    reviewer_name: str,
) -> tuple[str, dict]:
    if not _live(settings):
        tone = "grateful" if rating >= 4 else "empathetic"
        reply = (
            f"[DEV] Thanks {reviewer_name} — ({tone}, {rating}★). "
            f"We heard you{': ' + body[:80] if body else ''}. "
            f"{brand.voice.strip().split(chr(10))[0][:80]}"
        )
        return reply.strip(), {"mode": "dev", "action": "review_reply", "rating": rating}

    prompt = (
        f"=== Brand Brain ===\n{brand.as_prompt()}\n===\n\n"
        f"Write a short public reply to this {rating}-star review from {reviewer_name}.\n"
        f"Review: {body or '(no text)'}\n"
        "Rules: follow compliance (never discuss a patient's/customer's private details or "
        "confirm they are a patient), be specific to what they said, "
        + (
            "thank them warmly. "
            if rating >= 4
            else "apologise without admitting fault and invite them to contact the business directly. "
        )
        + "Under 80 words. Reply only, no quotes."
    )
    reply = await _chat(
        settings,
        system="You write brand-safe public review replies.",
        user=prompt,
        temperature=0.5,
    )
    return reply, {"mode": "openai", "model": settings.openai_chat_model, "action": "review_reply"}


async def tag_asset(
    settings: Settings,
    *,
    filename: str,
    data: bytes | None,
    content_type: str | None,
) -> tuple[list[str], dict]:
    """Assign category tags to an uploaded asset (vision model when live, filename hints in dev)."""
    if not _live(settings) or not data or not (content_type or "").startswith("image/"):
        return _dev_tags(filename), {"mode": "dev", "action": "tag"}

    data_url = f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"
    try:
        raw = await _chat(
            settings,
            system="You tag marketing photos for a local business media library.",
            user=[
                {
                    "type": "text",
                    "text": (
                        "Return 2-5 comma-separated lowercase tags for this photo. The first tag "
                        f"MUST be one of: {', '.join(ASSET_CATEGORIES)}. The rest describe the "
                        "subject (e.g. 'eyeglasses', 'smiling staff'). Tags only."
                    ),
                },
                {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
            ],
            temperature=0.0,
            timeout=60.0,
        )
    except Exception as exc:
        logger.exception("Asset tagging failed")
        return _dev_tags(filename), {"mode": "openai", "action": "tag", "error": str(exc)}
    tags = [t.strip().lower() for t in raw.split(",") if t.strip()][:5]
    return tags or ["uncategorized"], {"mode": "openai", "action": "tag"}


async def transcribe_audio(
    settings: Settings, *, data: bytes, filename: str, content_type: str | None
) -> tuple[str | None, dict]:
    """Story 1.2 voice notes → text (Whisper). Returns (None, meta) when transcription fails."""
    if not _live(settings):
        return "[DEV voice note] Please make the caption shorter and friendlier.", {
            "mode": "dev",
            "action": "transcribe",
        }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                data={"model": "whisper-1"},
                files={"file": (filename, data, content_type or "audio/webm")},
            )
            res.raise_for_status()
            text = (res.json().get("text") or "").strip()
    except Exception as exc:
        logger.exception("Voice note transcription failed")
        return None, {"mode": "openai", "action": "transcribe", "error": str(exc)}
    return text or None, {"mode": "openai", "action": "transcribe", "model": "whisper-1"}
