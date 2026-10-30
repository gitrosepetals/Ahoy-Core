"""
Regression: magic-link sign-in must work for seeded Captain and Crew.

Catches the class of failure behind the 2026-10-30 "Failed to fetch" incident —
API cannot talk to the A-hoy Postgres (wrong port / Windows Postgres clash /
missing seed) — by requiring a full sign-in for both roles against the seeded DB.
See docs/incident_log.md.
"""

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

# Seeded in packages/db/migrations/002_seed_oak_lawn.sql
CAPTAIN_PHONE = "+15551234001"
CREW_PHONE = "+15551234002"
OAK_LAWN_CLIENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _token_from_dev_link(dev_magic_link: str) -> str:
    query = parse_qs(urlparse(dev_magic_link).query)
    assert "token" in query and query["token"][0], "dev_magic_link missing token"
    return query["token"][0]


async def _sign_in(client: AsyncClient, phone: str, redirect_path: str) -> dict:
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

    token = _token_from_dev_link(body["dev_magic_link"])
    verified = await client.get(f"/api/v1/auth/verify?token={token}")
    assert verified.status_code == 200, verified.text
    return verified.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("phone", "role", "redirect_path"),
    [
        (CAPTAIN_PHONE, "captain", "/ship"),
        (CREW_PHONE, "crew", "/crew"),
    ],
)
async def test_magic_link_sign_in_for_seeded_roles(
    client: AsyncClient,
    settings,
    phone: str,
    role: str,
    redirect_path: str,
) -> None:
    assert settings.auth_dev_mode is True

    session = await _sign_in(client, phone, redirect_path)
    assert session["token_type"] == "bearer"
    assert session["access_token"]
    assert session["user"]["role"] == role
    assert session["user"]["phone_number"] == phone
    assert session["redirect_path"] == redirect_path
    assert OAK_LAWN_CLIENT_ID in session["user"]["client_ids"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert me.status_code == 200, me.text
    payload = me.json()
    assert payload["user"]["role"] == role
    assert any(c["client_id"] == OAK_LAWN_CLIENT_ID for c in payload["clients"])
    assert any(c["business_name"] == "Oak Lawn Optometry" for c in payload["clients"])


@pytest.mark.asyncio
async def test_captain_and_crew_are_different_users(client: AsyncClient) -> None:
    captain = await _sign_in(client, CAPTAIN_PHONE, "/ship")
    crew = await _sign_in(client, CREW_PHONE, "/crew")
    assert captain["user"]["user_id"] != crew["user"]["user_id"]
    assert captain["user"]["role"] == "captain"
    assert crew["user"]["role"] == "crew"
