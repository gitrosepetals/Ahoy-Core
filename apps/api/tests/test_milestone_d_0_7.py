"""Milestone D / 0.7.0: ROI correctness, Brand Brain context, campaign fan-out, Crew edit."""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.models import Client, DailyRoiMetric
from app.services.brand_context import BrandContext
from app.services.llm import _dev_tags
from app.services.roi import billing_period, summarize_roi
from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    OAK_LAWN_CLIENT_ID,
    auth_headers,
    sign_in_token,
)

CAPTAIN_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("anchor", "today", "expected_start"),
    [
        (1, date(2026, 11, 1), date(2026, 11, 1)),
        (15, date(2026, 11, 1), date(2026, 10, 15)),
        (15, date(2026, 11, 20), date(2026, 11, 15)),
        (28, date(2026, 3, 5), date(2026, 2, 28)),
        (10, date(2026, 1, 3), date(2025, 12, 10)),
    ],
)
def test_billing_period(anchor: int, today: date, expected_start: date) -> None:
    start, end = billing_period(anchor, today)
    assert start == expected_start
    assert end == today


@pytest.mark.unit
def test_brand_context_prompt_includes_every_field() -> None:
    prompt = BrandContext(
        business_name="Oak Lawn Optometry",
        voice="Warm",
        compliance="No guarantees",
        services={"services": [{"name": "Eye exam"}]},
        pricing="Exams from $150",
        seasonal_offers=[{"name": "FSA"}],
        zips=["60453"],
        seo_keywords=["Oak Lawn eye doctor"],
    ).as_prompt()
    for needle in ("Oak Lawn Optometry", "No guarantees", "Eye exam", "$150", "FSA", "60453",
                   "Oak Lawn eye doctor"):
        assert needle in prompt


@pytest.mark.unit
def test_dev_tags_use_prd_categories() -> None:
    assert _dev_tags("Team_portrait.jpg") == ["staff"]
    assert "exterior" in _dev_tags("storefront-sign.png")
    assert _dev_tags("IMG_0001.jpg") == ["uncategorized"]


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_bug001_estimate_not_dropped_on_partial_pos_days(db_session) -> None:
    """BUG-001 regression: a non-POS client keeps the formula even if a row has POS dollars."""
    today = datetime.now(ZoneInfo("America/Chicago")).date()
    client = Client(
        business_name="BUG-001 Test Co",
        industry_vertical="Test",
        owner_user_id=CAPTAIN_USER_ID,
        average_ticket_value=Decimal("100.00"),
        conversion_rate_estimate=Decimal("0.50"),
        billing_anchor_day=1,
    )
    db_session.add(client)
    await db_session.flush()
    db_session.add_all(
        [
            DailyRoiMetric(client_id=client.client_id, metric_date=today, tracked_calls_count=2,
                           form_leads_count=2, pos_attributed_revenue_usd=Decimal("999.00")),
            DailyRoiMetric(client_id=client.client_id, metric_date=today - timedelta(days=1),
                           tracked_calls_count=4, form_leads_count=0),
        ]
    )
    await db_session.flush()
    try:
        summary, breakdown = await summarize_roi(db_session, client.client_id, days=7)
        # (2+2+4) leads × 0.5 × $100 = $400, POS row ignored for a non-POS client
        assert summary["using_pos"] is False
        assert summary["estimated_revenue_usd"] == 400.0
        assert len(breakdown) == 2

        client.pos_provider = "square"
        await db_session.flush()
        summary, _ = await summarize_roi(db_session, client.client_id, days=7)
        assert summary["using_pos"] is True
        assert summary["estimated_revenue_usd"] == 999.0
    finally:
        await db_session.rollback()
        await db_session.execute(delete(Client).where(Client.business_name == "BUG-001 Test Co"))
        await db_session.commit()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_roi_defaults_to_billing_period(client: AsyncClient) -> None:
    token = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    res = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/roi",
        headers=auth_headers(token, OAK_LAWN_CLIENT_ID),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period"] == "billing"
    # Oak Lawn's local day (America/Chicago), not the test machine's
    assert body["period_end"] == datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    assert body["qualified_call_min_seconds"] == 60


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_brand_profile_new_fields_round_trip_and_partial_put(client: AsyncClient) -> None:
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    h = auth_headers(crew, OAK_LAWN_CLIENT_ID)
    url = f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/brand-profile"
    profile = (await client.get(url, headers=h)).json()

    base = {
        "brand_voice_guidelines": profile["brand_voice_guidelines"],
        "target_zip_codes": profile["target_zip_codes"],
        "compliance_rules": profile["compliance_rules"],
        "services_offered": profile["services_offered"],
    }
    put = await client.put(url, headers=h, json={**base, "pricing_notes": "Exams from $150",
                                                 "local_seo_keywords": ["Oak Lawn eye doctor"]})
    assert put.status_code == 200, put.text
    assert put.json()["pricing_notes"] == "Exams from $150"

    # Legacy body without the new fields must not null them out
    legacy = await client.put(url, headers=h, json=base)
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["pricing_notes"] == "Exams from $150"
    assert legacy.json()["local_seo_keywords"] == ["Oak Lawn eye doctor"]


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_campaign_fan_out_formats_per_channel(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    res = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=auth_headers(crew, OAK_LAWN_CLIENT_ID),
        json={
            "asset_ids": [],
            "channels": ["instagram_post", "gbp_update", "email_blast", "tiktok"],
            "days": 7,
            "count": 2,
            "fan_out": True,
        },
    )
    assert res.status_code == 201, res.text
    posts = res.json()
    assert len(posts) == 8
    assert len({p["generation_meta"]["batch_id"] for p in posts}) == 1
    by_channel = {p["channel"]: p["caption_text"] for p in posts}
    assert "#" in by_channel["instagram_post"]
    assert "#" in by_channel["tiktok"]
    assert "#" not in by_channel["gbp_update"]
    assert by_channel["email_blast"].startswith("Subject:")


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_crew_caption_edit(client: AsyncClient) -> None:
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=auth_headers(crew, OAK_LAWN_CLIENT_ID),
        json={"asset_ids": [], "channels": ["facebook"], "days": 3, "count": 1},
    )
    post_id = gen.json()[0]["post_id"]

    denied = await client.put(
        f"/api/v1/queue/{post_id}/caption",
        headers=auth_headers(captain),
        json={"caption_text": "Captain cannot hand-edit"},
    )
    assert denied.status_code == 403

    edited = await client.put(
        f"/api/v1/queue/{post_id}/caption",
        headers=auth_headers(crew),
        json={"caption_text": "Crew rewrite"},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["caption_text"] == "Crew rewrite"
    assert body["status"] == "draft_internal"
    assert body["generation_meta"]["needs_crew"] is False
