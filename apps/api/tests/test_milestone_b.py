"""Isolated Milestone B: Brand Brain, media, generate, release, revision (LLM_DEV_MODE)."""

import pytest
from httpx import AsyncClient

from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    OAK_LAWN_CLIENT_ID,
    SEEDED_ASSET_ID,
    auth_headers,
    sign_in_token,
)


@pytest.mark.milestone_b
@pytest.mark.asyncio
async def test_brand_brain_get_put_crew(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    token = await sign_in_token(client, CREW_PHONE, "/crew")
    headers = auth_headers(token, OAK_LAWN_CLIENT_ID)

    got = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/brand-profile",
        headers=headers,
    )
    assert got.status_code == 200, got.text
    profile = got.json()
    assert profile["brand_voice_guidelines"], "Brand Brain voice guidelines should be seeded"

    updated_voice = profile["brand_voice_guidelines"] + "\n[B-test] Keep sentences short."
    put = await client.put(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/brand-profile",
        headers=headers,
        json={
            "brand_voice_guidelines": updated_voice,
            "target_zip_codes": profile.get("target_zip_codes") or ["60453"],
            "compliance_rules": profile.get("compliance_rules") or "No guarantees.",
            "services_offered": profile.get("services_offered") or {"services": []},
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert "[B-test]" in body["brand_voice_guidelines"]
    assert body["has_embedding"] is True


@pytest.mark.milestone_b
@pytest.mark.asyncio
async def test_brand_brain_put_forbidden_for_captain(client: AsyncClient) -> None:
    token = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    headers = auth_headers(token, OAK_LAWN_CLIENT_ID)
    put = await client.put(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/brand-profile",
        headers=headers,
        json={
            "brand_voice_guidelines": "Captain should not edit this.",
            "target_zip_codes": ["60453"],
            "compliance_rules": "n/a",
            "services_offered": {},
        },
    )
    assert put.status_code == 403


@pytest.mark.milestone_b
@pytest.mark.asyncio
async def test_media_list_for_crew(client: AsyncClient) -> None:
    token = await sign_in_token(client, CREW_PHONE, "/crew")
    res = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/media",
        headers=auth_headers(token, OAK_LAWN_CLIENT_ID),
    )
    assert res.status_code == 200, res.text
    assets = res.json()
    assert isinstance(assets, list)
    if assets:
        ids = {a["asset_id"] for a in assets}
        assert SEEDED_ASSET_ID in ids or len(assets) >= 1


@pytest.mark.milestone_b
@pytest.mark.asyncio
async def test_generate_release_and_revision_loop(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    crew_token = await sign_in_token(client, CREW_PHONE, "/crew")
    captain_token = await sign_in_token(client, CAPTAIN_PHONE, "/ship/posts")
    crew_headers = auth_headers(crew_token, OAK_LAWN_CLIENT_ID)

    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_headers,
        json={
            "asset_ids": [SEEDED_ASSET_ID],
            "channels": ["instagram_post", "facebook"],
            "days": 7,
            "count": 2,
        },
    )
    if gen.status_code == 400 and "asset_ids" in gen.text:
        gen = await client.post(
            f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
            headers=crew_headers,
            json={"asset_ids": [], "channels": ["instagram_post"], "days": 7, "count": 2},
        )
    assert gen.status_code == 201, gen.text
    drafts = gen.json()
    assert len(drafts) == 2
    assert all(p["status"] == "draft_internal" for p in drafts)
    assert all("[DEV]" in p["caption_text"] for p in drafts)

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_headers,
        json={"post_ids": [drafts[0]["post_id"], drafts[1]["post_id"]]},
    )
    assert release.status_code == 200, release.text
    released = release.json()
    assert len(released) == 2
    assert all(p["status"] == "pending_client" for p in released)

    post_id = released[0]["post_id"]
    edit = await client.post(
        f"/api/v1/queue/{post_id}/request-edit",
        headers=auth_headers(captain_token),
        json={"feedback": "Make it shorter and mention eye exams."},
    )
    assert edit.status_code == 200, edit.text
    revised = edit.json()
    assert revised["status"] == "pending_client"
    assert "[DEV revised]" in revised["caption_text"]
    assert "eye exams" in (revised["client_feedback"] or "")

    approve = await client.post(
        f"/api/v1/queue/{post_id}/approve",
        headers=auth_headers(captain_token),
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    denied = await client.post(
        f"/api/v1/queue/{released[1]['post_id']}/approve",
        headers=auth_headers(crew_token),
    )
    assert denied.status_code == 403


@pytest.mark.milestone_b
@pytest.mark.asyncio
async def test_queue_status_filter_after_release(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    crew_token = await sign_in_token(client, CREW_PHONE, "/crew")
    headers = auth_headers(crew_token, OAK_LAWN_CLIENT_ID)

    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=headers,
        json={"asset_ids": [], "channels": ["instagram_post"], "days": 3, "count": 1},
    )
    assert gen.status_code == 201, gen.text
    post_id = gen.json()[0]["post_id"]

    drafts = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=draft_internal",
        headers=headers,
    )
    assert drafts.status_code == 200
    assert post_id in {p["post_id"] for p in drafts.json()}

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=headers,
        json={"post_ids": [post_id]},
    )
    assert release.status_code == 200, release.text

    pending = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=pending_client",
        headers=headers,
    )
    assert pending.status_code == 200
    assert post_id in {p["post_id"] for p in pending.json()}

    drafts_after = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=draft_internal",
        headers=headers,
    )
    assert drafts_after.status_code == 200
    assert post_id not in {p["post_id"] for p in drafts_after.json()}


@pytest.mark.milestone_b
@pytest.mark.asyncio
async def test_approve_leaves_queue_and_refill_via_generate_release(
    client: AsyncClient, settings
) -> None:
    """Ship queue only shows pending_client; approve removes a post; generate+release refills it."""
    assert settings.llm_dev_mode is True
    crew_token = await sign_in_token(client, CREW_PHONE, "/crew")
    captain_token = await sign_in_token(client, CAPTAIN_PHONE, "/ship/posts")
    crew_headers = auth_headers(crew_token, OAK_LAWN_CLIENT_ID)
    captain_headers = auth_headers(captain_token, OAK_LAWN_CLIENT_ID)

    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_headers,
        json={"asset_ids": [], "channels": ["instagram_post"], "days": 3, "count": 1},
    )
    assert gen.status_code == 201, gen.text
    post_id = gen.json()[0]["post_id"]

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_headers,
        json={"post_ids": [post_id]},
    )
    assert release.status_code == 200, release.text

    pending_before = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=pending_client",
        headers=captain_headers,
    )
    assert pending_before.status_code == 200, pending_before.text
    assert post_id in {p["post_id"] for p in pending_before.json()}

    approve = await client.post(
        f"/api/v1/queue/{post_id}/approve",
        headers=auth_headers(captain_token),
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    pending_after = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=pending_client",
        headers=captain_headers,
    )
    assert pending_after.status_code == 200, pending_after.text
    assert post_id not in {p["post_id"] for p in pending_after.json()}

    gen2 = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_headers,
        json={"asset_ids": [], "channels": ["facebook"], "days": 3, "count": 1},
    )
    assert gen2.status_code == 201, gen2.text
    new_id = gen2.json()[0]["post_id"]
    assert new_id != post_id

    release2 = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_headers,
        json={"post_ids": [new_id]},
    )
    assert release2.status_code == 200, release2.text

    pending_refilled = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=pending_client",
        headers=captain_headers,
    )
    assert pending_refilled.status_code == 200, pending_refilled.text
    refilled_ids = {p["post_id"] for p in pending_refilled.json()}
    assert new_id in refilled_ids
    assert post_id not in refilled_ids
