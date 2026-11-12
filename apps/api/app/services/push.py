"""Firebase Cloud Messaging (HTTP v1) push for Ship devices — iOS, Android and web via FCM."""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from pathlib import Path

import httpx
from jose import jwt

from app.config import Settings

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_token_cache: dict[str, tuple[str, float]] = {}


def push_enabled(settings: Settings) -> bool:
    return bool(settings.fcm_project_id and settings.fcm_service_account_file)


@lru_cache
def _service_account(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


async def _access_token(settings: Settings) -> str:
    cached = _token_cache.get(settings.fcm_service_account_file)
    if cached and cached[1] > time.time() + 60:
        return cached[0]
    sa = _service_account(settings.fcm_service_account_file)
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": sa["client_email"],
            "scope": FCM_SCOPE,
            "aud": sa.get("token_uri", "https://oauth2.googleapis.com/token"),
            "iat": now,
            "exp": now + 3600,
        },
        sa["private_key"],
        algorithm="RS256",
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            sa.get("token_uri", "https://oauth2.googleapis.com/token"),
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        )
        res.raise_for_status()
        data = res.json()
    _token_cache[settings.fcm_service_account_file] = (
        data["access_token"],
        time.time() + int(data.get("expires_in", 3600)),
    )
    return data["access_token"]


class PushTokenInvalid(Exception):
    """FCM says the device token is gone — caller should disable it."""


async def send_push(
    settings: Settings,
    *,
    token: str,
    title: str,
    body: str,
    data: dict[str, str],
) -> str:
    """Send to one device token. Returns the FCM message name."""
    access = await _access_token(settings)
    url = f"https://fcm.googleapis.com/v1/projects/{settings.fcm_project_id}/messages:send"
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            url,
            headers={"Authorization": f"Bearer {access}"},
            json={
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                    "data": data,
                    "webpush": {"fcm_options": {"link": data.get("path", "/ship")}},
                }
            },
        )
    if res.status_code in (404, 410) or "UNREGISTERED" in res.text:
        raise PushTokenInvalid(res.text[:200])
    if res.status_code >= 400:
        raise RuntimeError(f"FCM {res.status_code}: {res.text[:300]}")
    return str(res.json().get("name", ""))
