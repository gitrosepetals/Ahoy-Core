"""Async Twilio SMS (fixes BUG-002: the twilio SDK call was blocking the event loop)."""

from __future__ import annotations

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

TWILIO_API = "https://api.twilio.com/2010-04-01"


def sms_enabled(settings: Settings) -> bool:
    return bool(
        not settings.auth_dev_mode
        and settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    )


async def send_sms(settings: Settings, *, to: str, body: str) -> str:
    """Send one SMS; returns the Twilio message SID. Raises on failure."""
    url = f"{TWILIO_API}/Accounts/{settings.twilio_account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={"To": to, "From": settings.twilio_from_number, "Body": body},
        )
    if res.status_code >= 400:
        raise RuntimeError(f"Twilio {res.status_code}: {res.text[:300]}")
    return str(res.json().get("sid", ""))
