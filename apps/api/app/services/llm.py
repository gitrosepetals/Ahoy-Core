"""LLM helpers: OpenAI when configured, deterministic stub when LLM_DEV_MODE."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
EMBED_DIM = 1536


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


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


def _dev_caption(*, channel: str, brand_voice: str, asset_tags: list[str] | None, index: int) -> str:
    tags = ", ".join(asset_tags or ["general"])
    voice_snip = (brand_voice or "Friendly local tone").strip().split("\n")[0][:120]
    return (
        f"[DEV] {channel.replace('_', ' ').title()} post #{index + 1}: "
        f"Highlight {tags} for our community. {voice_snip}"
    )


def _dev_revise(caption: str, feedback: str) -> str:
    return f"[DEV revised] {caption}\n\n(Addressed: {feedback.strip()[:200]})"


async def embed_text(settings: Settings, text: str) -> list[float]:
    if settings.llm_dev_mode or not settings.openai_api_key:
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
    brand_voice: str,
    compliance: str | None,
    services: object,
    channel: str,
    asset_tags: list[str] | None,
    asset_notes: str,
    index: int = 0,
) -> tuple[str, dict]:
    if settings.llm_dev_mode or not settings.openai_api_key:
        caption = _dev_caption(
            channel=channel, brand_voice=brand_voice, asset_tags=asset_tags, index=index
        )
        return caption, {"mode": "dev", "channel": channel, "index": index}

    template = _load_prompt("caption_batch.txt")
    prompt = template.format(
        brand_voice=brand_voice,
        compliance=compliance or "(none)",
        services=json.dumps(services) if services is not None else "(none)",
        channel=channel,
        asset_tags=", ".join(asset_tags or []) or "(none)",
        asset_notes=asset_notes or "(none)",
    )
    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_chat_model,
                "messages": [
                    {"role": "system", "content": "You write compliant local-business social captions."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
            },
        )
        res.raise_for_status()
        data = res.json()
        caption = data["choices"][0]["message"]["content"].strip()
        return caption, {"mode": "openai", "model": settings.openai_chat_model, "channel": channel}


async def revise_caption(
    settings: Settings,
    *,
    brand_voice: str,
    compliance: str | None,
    caption: str,
    feedback: str,
) -> tuple[str | None, dict]:
    """Return (new_caption, meta). new_caption is None if rewrite should be flagged for Crew."""
    if settings.llm_dev_mode or not settings.openai_api_key:
        return _dev_revise(caption, feedback), {"mode": "dev", "action": "revise"}

    template = _load_prompt("caption_revision.txt")
    prompt = template.format(
        brand_voice=brand_voice,
        compliance=compliance or "(none)",
        caption=caption,
        feedback=feedback,
    )
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_chat_model,
                    "messages": [
                        {"role": "system", "content": "You revise captions from client feedback."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                },
            )
            res.raise_for_status()
            data = res.json()
            revised = data["choices"][0]["message"]["content"].strip()
            if not revised:
                return None, {"mode": "openai", "action": "revise", "error": "empty_response"}
            return revised, {"mode": "openai", "model": settings.openai_chat_model, "action": "revise"}
    except Exception as exc:
        logger.exception("Caption revision failed")
        return None, {"mode": "openai", "action": "revise", "error": str(exc)}


async def draft_review_reply(
    settings: Settings,
    *,
    brand_voice: str,
    rating: int,
    body: str,
    reviewer_name: str,
) -> tuple[str, dict]:
    if settings.llm_dev_mode or not settings.openai_api_key:
        tone = "grateful" if rating >= 4 else "empathetic"
        reply = (
            f"[DEV] Thanks {reviewer_name} — ({tone}, {rating}★). "
            f"We heard you{': ' + body[:80] if body else ''}. "
            f"{brand_voice.strip().split(chr(10))[0][:80]}"
        )
        return reply.strip(), {"mode": "dev", "action": "review_reply", "rating": rating}

    prompt = (
        f"Brand voice:\n{brand_voice}\n\n"
        f"Write a short public reply to this {rating}-star review from {reviewer_name}.\n"
        f"Review: {body or '(no text)'}\n"
        "Reply only, no quotes."
    )
    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_chat_model,
                "messages": [
                    {"role": "system", "content": "You write brand-safe public review replies."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.5,
            },
        )
        res.raise_for_status()
        data = res.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return reply, {"mode": "openai", "model": settings.openai_chat_model, "action": "review_reply"}
