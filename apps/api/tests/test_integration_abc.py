"""
Integration A↔B↔C: auth/roles from A, content pipeline from B, Ship polish from C.
"""

import pytest
from httpx import AsyncClient

from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    FOREIGN_CLIENT_ID,
    LOW_STAR_REVIEW_ID,
    OAK_LAWN_CLIENT_ID,
    SEEDED_ASSET_ID,
    auth_headers,
    sign_in,
)


@pytest.mark.integration_abc
@pytest.mark.asyncio
async def test_abc_auth_pipeline_roi_swap_approve_and_review(
    client: AsyncClient, settings
) -> None:
    assert settings.auth_dev_mode is True
    assert settings.llm_dev_mode is True

    # --- A: sessions + roles ---
    crew = await sign_in(client, CREW_PHONE, "/crew")
    captain = await sign_in(client, CAPTAIN_PHONE, "/ship/posts")
    crew_token = crew["access_token"]
    captain_token = captain["access_token"]
    assert crew["user"]["role"] == "crew"
    assert captain["user"]["role"] == "captain"
    assert crew["user"]["user_id"] != captain["user"]["user_id"]

    crew_h = auth_headers(crew_token, OAK_LAWN_CLIENT_ID)
    cap_h = auth_headers(captain_token, OAK_LAWN_CLIENT_ID)

    # --- C: Treasure Map (Captain) ---
    roi = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/roi?days=30",
        headers=cap_h,
    )
    assert roi.status_code == 200, roi.text
    assert roi.json()["total_leads"] == (
        roi.json()["total_calls"] + roi.json()["total_form_leads"]
    )

    # A×C: Crew cannot approve-all
    denied_approve_all = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/approve-all",
        headers=crew_h,
    )
    assert denied_approve_all.status_code == 403

    # --- B: generate → release ---
    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_h,
        json={"asset_ids": [], "channels": ["instagram_post"], "days": 4, "count": 2},
    )
    assert gen.status_code == 201, gen.text
    post_ids = [p["post_id"] for p in gen.json()]
    assert len(post_ids) == 2

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_h,
        json={"post_ids": post_ids},
    )
    assert release.status_code == 200, release.text
    assert all(p["status"] == "pending_client" for p in release.json())

    # --- C: swap media on first pending post ---
    media = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/media",
        headers=cap_h,
    )
    assert media.status_code == 200, media.text
    assets = media.json()
    asset_id = next(
        (a["asset_id"] for a in assets if a["asset_id"] == SEEDED_ASSET_ID),
        assets[0]["asset_id"] if assets else None,
    )
    if asset_id is None:
        pytest.skip("Media seed 003 not applied")

    swap = await client.post(
        f"/api/v1/queue/{post_ids[0]}/swap-asset",
        headers=auth_headers(captain_token),
        json={"asset_id": asset_id},
    )
    assert swap.status_code == 200, swap.text
    assert swap.json()["asset_id"] == asset_id
    assert swap.json()["status"] == "pending_client"

    # --- C: Captain approve-all empties pending ---
    approved = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/approve-all",
        headers=cap_h,
    )
    assert approved.status_code == 200, approved.text
    approved_ids = {p["post_id"] for p in approved.json()}
    assert post_ids[0] in approved_ids and post_ids[1] in approved_ids
    assert all(p["status"] == "approved" for p in approved.json())

    pending = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue?status=pending_client",
        headers=cap_h,
    )
    assert pending.status_code == 200
    leftover = {p["post_id"] for p in pending.json()}
    assert post_ids[0] not in leftover and post_ids[1] not in leftover

    # --- C: Reputation Radar (seed 004); approve is idempotent ---
    reviews = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/reviews",
        headers=cap_h,
    )
    assert reviews.status_code == 200, reviews.text
    rows = reviews.json()
    if not rows:
        pytest.skip("Review seed 004 not applied")

    target = next((r for r in rows if r["review_id"] == LOW_STAR_REVIEW_ID), None)
    if target is None:
        target = next((r for r in rows if r["rating"] <= 3), rows[0])
    assert target.get("ai_reply")

    denied_reply = await client.post(
        f"/api/v1/reviews/{target['review_id']}/approve-reply",
        headers=auth_headers(crew_token),
    )
    assert denied_reply.status_code == 403

    reply = await client.post(
        f"/api/v1/reviews/{target['review_id']}/approve-reply",
        headers=auth_headers(captain_token),
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["reply_status"] == "captain_approved"

    # A tenancy still gates C routes
    foreign_roi = await client.get(
        f"/api/v1/clients/{FOREIGN_CLIENT_ID}/roi",
        headers=auth_headers(captain_token, FOREIGN_CLIENT_ID),
    )
    assert foreign_roi.status_code == 403
