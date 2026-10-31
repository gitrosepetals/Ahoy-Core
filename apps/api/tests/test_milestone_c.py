"""Isolated Milestone C: ROI, swap-asset, approve-all, reviews (LLM_DEV_MODE)."""

import pytest
from httpx import AsyncClient

from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    LOW_STAR_REVIEW_ID,
    OAK_LAWN_CLIENT_ID,
    SEEDED_ASSET_ID,
    auth_headers,
    sign_in_token,
)


@pytest.mark.milestone_c
@pytest.mark.asyncio
async def test_roi_summary_and_breakdown(client: AsyncClient) -> None:
    token = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    headers = auth_headers(token, OAK_LAWN_CLIENT_ID)

    roi = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/roi?days=30",
        headers=headers,
    )
    assert roi.status_code == 200, roi.text
    body = roi.json()
    assert body["client_id"] == OAK_LAWN_CLIENT_ID
    assert body["total_leads"] == body["total_calls"] + body["total_form_leads"]
    assert body["estimated_revenue_usd"] >= 0
    assert body["average_ticket_value"] > 0

    breakdown = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/roi/breakdown?days=30",
        headers=headers,
    )
    assert breakdown.status_code == 200, breakdown.text
    assert isinstance(breakdown.json(), list)


@pytest.mark.milestone_c
@pytest.mark.asyncio
async def test_swap_asset_on_pending_post(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship/posts")
    crew_h = auth_headers(crew, OAK_LAWN_CLIENT_ID)

    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_h,
        json={"asset_ids": [], "channels": ["instagram_post"], "days": 3, "count": 1},
    )
    assert gen.status_code == 201, gen.text
    post_id = gen.json()[0]["post_id"]

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_h,
        json={"post_ids": [post_id]},
    )
    assert release.status_code == 200, release.text

    media = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/media",
        headers=auth_headers(captain, OAK_LAWN_CLIENT_ID),
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
        f"/api/v1/queue/{post_id}/swap-asset",
        headers=auth_headers(captain),
        json={"asset_id": asset_id},
    )
    assert swap.status_code == 200, swap.text
    assert swap.json()["asset_id"] == asset_id
    assert swap.json()["status"] == "pending_client"

    # Crew cannot swap (Captain-only)
    denied = await client.post(
        f"/api/v1/queue/{post_id}/swap-asset",
        headers=auth_headers(crew),
        json={"asset_id": asset_id},
    )
    assert denied.status_code == 403


@pytest.mark.milestone_c
@pytest.mark.asyncio
async def test_approve_all_pending_posts(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship/posts")
    crew_h = auth_headers(crew, OAK_LAWN_CLIENT_ID)
    cap_h = auth_headers(captain, OAK_LAWN_CLIENT_ID)

    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_h,
        json={"asset_ids": [], "channels": ["facebook"], "days": 3, "count": 2},
    )
    assert gen.status_code == 201, gen.text
    ids = [p["post_id"] for p in gen.json()]

    release = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_h,
        json={"post_ids": ids},
    )
    assert release.status_code == 200, release.text

    denied = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/approve-all",
        headers=crew_h,
    )
    assert denied.status_code == 403

    approve_all = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/approve-all",
        headers=cap_h,
    )
    assert approve_all.status_code == 200, approve_all.text
    body = approve_all.json()
    approved_ids = {p["post_id"] for p in body}
    assert ids[0] in approved_ids and ids[1] in approved_ids
    assert all(p["status"] == "approved" for p in body)


@pytest.mark.milestone_c
@pytest.mark.asyncio
async def test_reviews_list_and_approve_reply(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship/reviews")
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    cap_h = auth_headers(captain, OAK_LAWN_CLIENT_ID)

    listed = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/reviews",
        headers=cap_h,
    )
    assert listed.status_code == 200, listed.text
    reviews = listed.json()
    assert isinstance(reviews, list)
    if not reviews:
        pytest.skip("Review seed 004 not applied")

    low = next((r for r in reviews if r["review_id"] == LOW_STAR_REVIEW_ID), None)
    if low is None:
        low = next((r for r in reviews if r["rating"] <= 3), None)
    if low is None:
        pytest.skip("No low-star review in seed")
    assert low.get("ai_reply"), "Expected AI reply draft on low-star review"

    denied = await client.post(
        f"/api/v1/reviews/{low['review_id']}/approve-reply",
        headers=auth_headers(crew),
    )
    assert denied.status_code == 403

    # Idempotent: first run moves awaiting_captain → captain_approved; re-runs stay approved.
    approved = await client.post(
        f"/api/v1/reviews/{low['review_id']}/approve-reply",
        headers=auth_headers(captain),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["reply_status"] == "captain_approved"
