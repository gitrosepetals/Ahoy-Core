"""
Integration A↔B: Milestone A auth/tenancy still gates the Milestone B content loop.
"""

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


@pytest.mark.integration_ab
@pytest.mark.asyncio
async def test_ab_crew_to_captain_pipeline_with_role_and_tenant_gates(
    client: AsyncClient, settings
) -> None:
    assert settings.auth_dev_mode is True
    assert settings.llm_dev_mode is True

    # --- A: distinct sessions ---
    crew_session = await sign_in(client, CREW_PHONE, "/crew")
    captain_session = await sign_in(client, CAPTAIN_PHONE, "/ship/posts")
    crew_token = crew_session["access_token"]
    captain_token = captain_session["access_token"]
    assert crew_session["user"]["user_id"] != captain_session["user"]["user_id"]
    assert crew_session["user"]["role"] == "crew"
    assert captain_session["user"]["role"] == "captain"

    crew_headers = auth_headers(crew_token, OAK_LAWN_CLIENT_ID)
    captain_headers = auth_headers(captain_token, OAK_LAWN_CLIENT_ID)

    # A: Captain registers push token so notify stub can prefer push_stub
    push_value = f"ab-int-push-{captain_session['user']['user_id']}"
    push_reg = await client.post(
        "/api/v1/devices/push-token",
        headers=auth_headers(captain_token),
        json={"token": push_value, "platform": "web"},
    )
    assert push_reg.status_code == 200, push_reg.text

    # --- B: Brand Brain via Crew JWT from A ---
    got = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/brand-profile",
        headers=crew_headers,
    )
    assert got.status_code == 200, got.text
    profile = got.json()
    put = await client.put(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/brand-profile",
        headers=crew_headers,
        json={
            "brand_voice_guidelines": profile["brand_voice_guidelines"] + "\n[AB-int]",
            "target_zip_codes": profile.get("target_zip_codes") or ["60453"],
            "compliance_rules": profile.get("compliance_rules") or "No guarantees.",
            "services_offered": profile.get("services_offered") or {},
        },
    )
    assert put.status_code == 200, put.text
    assert put.json()["has_embedding"] is True
    assert "[AB-int]" in put.json()["brand_voice_guidelines"]

    # --- B: generate → draft → release → pending (+ notify meta) ---
    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_headers,
        json={"asset_ids": [], "channels": ["instagram_post"], "days": 5, "count": 1},
    )
    assert gen.status_code == 201, gen.text
    draft = gen.json()[0]
    assert draft["status"] == "draft_internal"
    post_id = draft["post_id"]

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_headers,
        json={"post_ids": [post_id]},
    )
    assert release.status_code == 200, release.text
    released = release.json()[0]
    assert released["status"] == "pending_client"
    notify = (released.get("generation_meta") or {}).get("last_notify") or {}
    assert notify.get("channel") in {"push_stub", "log", "sms_stub"}

    # --- A×B: Captain sees pending; request-edit; approve ---
    pending = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=pending_client",
        headers=captain_headers,
    )
    assert pending.status_code == 200, pending.text
    assert post_id in {p["post_id"] for p in pending.json()}

    edit = await client.post(
        f"/api/v1/queue/{post_id}/request-edit",
        headers=auth_headers(captain_token),
        json={"feedback": "Mention Oak Lawn neighborhood."},
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["status"] == "pending_client"
    assert "[DEV revised]" in edit.json()["caption_text"]

    # A role gate: Crew cannot approve Captain's post
    denied = await client.post(
        f"/api/v1/queue/{post_id}/approve",
        headers=auth_headers(crew_token),
    )
    assert denied.status_code == 403

    approve = await client.post(
        f"/api/v1/queue/{post_id}/approve",
        headers=auth_headers(captain_token),
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    # A tenancy: foreign client on a B route → 403
    foreign = await client.get(
        f"/api/v1/clients/{FOREIGN_CLIENT_ID}/brand-profile",
        headers=auth_headers(crew_token, FOREIGN_CLIENT_ID),
    )
    assert foreign.status_code == 403

    mismatched_header = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue",
        headers=auth_headers(crew_token, FOREIGN_CLIENT_ID),
    )
    assert mismatched_header.status_code == 400
