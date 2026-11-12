"""Validate Twilio webhook signatures (X-Twilio-Signature)."""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Mapping

from app.config import Settings


def compute_signature(auth_token: str, url: str, params: Mapping[str, str]) -> str:
    payload = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def signature_required(settings: Settings) -> bool:
    """Enforced whenever a real Twilio auth token is configured outside dev mode."""
    return bool(settings.twilio_auth_token) and not settings.auth_dev_mode


def is_valid(
    settings: Settings, *, url: str, params: Mapping[str, str], signature: str | None
) -> bool:
    if not signature_required(settings):
        return True
    if not signature:
        return False
    expected = compute_signature(settings.twilio_auth_token, url, params)
    return hmac.compare_digest(expected, signature)
