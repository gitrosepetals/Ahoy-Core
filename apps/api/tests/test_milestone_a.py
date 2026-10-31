"""Isolated Milestone A: auth, tenancy, push tokens, health (no Brand Brain / generate)."""

import pytest
from httpx import AsyncClient

from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    FOREIGN_CLIENT_ID,
    OAK_LAWN_CLIENT_ID,
    auth_headers,
    sign_in,
)


@pytest.mark.milestone_a
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

    session = await sign_in(client, phone, redirect_path)
    assert session["token_type"] == "bearer"
    assert session["access_token"]
    assert session["user"]["role"] == role
    assert session["user"]["phone_number"] == phone
    assert session["redirect_path"] == redirect_path
    assert OAK_LAWN_CLIENT_ID in session["user"]["client_ids"]

    me = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers(session["access_token"]),
    )
    assert me.status_code == 200, me.text
    payload = me.json()
    assert payload["user"]["role"] == role
    assert any(c["client_id"] == OAK_LAWN_CLIENT_ID for c in payload["clients"])
    assert any(c["business_name"] == "Oak Lawn Optometry" for c in payload["clients"])


@pytest.mark.milestone_a
@pytest.mark.asyncio
async def test_captain_and_crew_are_different_users(client: AsyncClient) -> None:
    captain = await sign_in(client, CAPTAIN_PHONE, "/ship")
    crew = await sign_in(client, CREW_PHONE, "/crew")
    assert captain["user"]["user_id"] != crew["user"]["user_id"]
    assert captain["user"]["role"] == "captain"
    assert crew["user"]["role"] == "crew"


@pytest.mark.milestone_a
@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.milestone_a
@pytest.mark.asyncio
async def test_tenant_gate_rejects_foreign_client(client: AsyncClient) -> None:
    session = await sign_in(client, CAPTAIN_PHONE, "/ship")
    res = await client.get(
        f"/api/v1/clients/{FOREIGN_CLIENT_ID}",
        headers=auth_headers(session["access_token"], FOREIGN_CLIENT_ID),
    )
    assert res.status_code == 403


@pytest.mark.milestone_a
@pytest.mark.asyncio
async def test_push_token_register_and_disable(client: AsyncClient) -> None:
    session = await sign_in(client, CAPTAIN_PHONE, "/ship")
    token = session["access_token"]
    push_value = f"test-push-token-a-{session['user']['user_id']}"

    register = await client.post(
        "/api/v1/devices/push-token",
        headers=auth_headers(token),
        json={"token": push_value, "platform": "web"},
    )
    assert register.status_code == 200, register.text
    body = register.json()
    assert body["ok"] is True
    assert body["platform"] == "web"
    assert body["token_id"]

    disable = await client.delete(
        "/api/v1/devices/push-token",
        headers=auth_headers(token),
        params={"token": push_value},
    )
    assert disable.status_code == 204, disable.text
