"""Shared seed constants and auth helpers for Milestone A/B/C tests."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient

# Seeded in packages/db/migrations/002_seed_oak_lawn.sql
CAPTAIN_PHONE = "+15551234001"
CREW_PHONE = "+15551234002"
OAK_LAWN_CLIENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
# Seeded in packages/db/migrations/003_seed_oak_lawn_media.sql
SEEDED_ASSET_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
# Seeded in packages/db/migrations/004_seed_oak_lawn_reviews.sql (2★ awaiting Captain)
LOW_STAR_REVIEW_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc3"
FOREIGN_CLIENT_ID = "99999999-9999-9999-9999-999999999999"


def token_from_dev_link(dev_magic_link: str) -> str:
    query = parse_qs(urlparse(dev_magic_link).query)
    assert "token" in query and query["token"][0], "dev_magic_link missing token"
    return query["token"][0]


def auth_headers(token: str, client_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if client_id:
        headers["X-Client-Id"] = client_id
    return headers


async def sign_in(client: AsyncClient, phone: str, redirect_path: str) -> dict:
    """Full magic-link sign-in; returns verify JSON (access_token, user, …)."""
    res = await client.post(
        "/api/v1/auth/magic-link",
        json={"phone_number": phone, "redirect_path": redirect_path},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("dev_magic_link"), (
        "Expected dev_magic_link (set AUTH_DEV_MODE=true). "
        "If this is 200 without a link, seed user may be missing."
    )
    verified = await client.get(
        f"/api/v1/auth/verify?token={token_from_dev_link(body['dev_magic_link'])}"
    )
    assert verified.status_code == 200, verified.text
    return verified.json()


async def sign_in_token(client: AsyncClient, phone: str, redirect_path: str) -> str:
    session = await sign_in(client, phone, redirect_path)
    return session["access_token"]
