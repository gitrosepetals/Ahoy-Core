"""Milestone D / 0.11.0: review sync (Google / Facebook / Yelp), reply posting, auto-reply delay."""

import json
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import Settings, get_settings
from app.main import app
from app.models import DailyRoiMetric, Notification, ReplyStatus, Review, ReviewProvider
from app.services import review_providers as rp
from app.services.credentials import get_credential, put_credential
from app.services.reviews import ingest_reviews, post_due_review_replies, upsert_performance
from tests.helpers import CAPTAIN_PHONE, CREW_PHONE, auth_headers, sign_in_token


def _mock_httpx(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(
        rp.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_parsers(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "mybusiness.googleapis.com" in url:
            return httpx.Response(200, json={"reviews": [
                {"reviewId": "g1", "starRating": "FOUR", "comment": "Nice", "createTime": "2026-10-30T10:00:00.5Z",
                 "reviewer": {"displayName": "Ana"}},
                {"reviewId": "g2", "starRating": "ONE", "reviewReply": {"comment": "Sorry!"}},
                {"reviewId": "g3", "starRating": "STAR_RATING_UNSPECIFIED"},
            ]})
        if "graph.facebook.com" in url:
            return httpx.Response(200, json={"data": [
                {"recommendation_type": "negative", "review_text": "Meh", "created_time": "2026-10-30T10:00:00+0000",
                 "reviewer": {"name": "Bo"}, "open_graph_story": {"id": "story1"}},
            ]})
        return httpx.Response(200, json={"reviews": [
            {"id": "y1", "rating": 5, "text": "Great", "time_created": "2026-10-29 09:00:00", "user": {"name": "Cy"}},
        ]})

    _mock_httpx(monkeypatch, handler)
    google = await rp.google_fetch_reviews("tok", "accounts/1/locations/2")
    assert [(r.external_id, r.rating) for r in google] == [("g1", 4), ("g2", 1)]
    assert google[1].existing_reply == "Sorry!"
    assert google[0].reviewer_name == "Ana" and google[0].reviewed_at.year == 2026

    fb = await rp.facebook_fetch_reviews("page1", "token")
    assert fb[0].rating == 2 and fb[0].reply_target == "story1"

    yelp = await rp.yelp_fetch_reviews("key", "biz")
    assert yelp[0].rating == 5 and yelp[0].reviewed_at.tzinfo is not None
    assert not rp.provider_can_reply(ReviewProvider.yelp)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gbp_performance_parser(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert ":fetchMultiDailyMetricsTimeSeries" in str(request.url)
        point = lambda v: {"date": {"year": 2026, "month": 10, "day": 31}, "value": v}
        return httpx.Response(200, json={"multiDailyMetricTimeSeries": [{"dailyMetricTimeSeries": [
            {"dailyMetric": "BUSINESS_IMPRESSIONS_MOBILE_MAPS", "timeSeries": {"datedValues": [point("40")]}},
            {"dailyMetric": "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", "timeSeries": {"datedValues": [point("10")]}},
            {"dailyMetric": "BUSINESS_DIRECTION_REQUESTS", "timeSeries": {"datedValues": [point("3")]}},
            {"dailyMetric": "CALL_CLICKS", "timeSeries": {"datedValues": [point("2")]}},
        ]}]})

    _mock_httpx(monkeypatch, handler)
    out = await rp.google_fetch_performance("tok", "accounts/1/locations/2", date(2026, 10, 25), date(2026, 10, 31))
    assert out == {date(2026, 10, 31): {"impressions": 50, "gbp_direction_requests": 3, "clicks": 2}}


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_ingest_schedules_alerts_and_skips(db_session, settings, temp_client) -> None:
    temp_client.auto_reply_delay_hours = 24
    fetched = [
        rp.FetchedReview("r5", 5, "Loved it", "Dee", datetime.now(UTC)),
        rp.FetchedReview("r2", 2, "Slow", "Eli", datetime.now(UTC)),
        rp.FetchedReview("r4", 4, "Good", "Fay", datetime.now(UTC), existing_reply="Thanks Fay!"),
    ]
    new = await ingest_reviews(db_session, settings, temp_client, ReviewProvider.google, fetched)
    assert new == 3
    assert await ingest_reviews(db_session, settings, temp_client, ReviewProvider.google, fetched) == 0

    rows = {
        r.external_id: r
        for r in (
            await db_session.execute(select(Review).where(Review.client_id == temp_client.client_id))
        ).scalars()
    }
    five, two, four = rows["r5"], rows["r2"], rows["r4"]
    assert five.reply_status == ReplyStatus.scheduled and five.ai_reply
    assert timedelta(hours=23) < five.reply_due_at - datetime.now(UTC) <= timedelta(hours=24)
    assert two.reply_status == ReplyStatus.awaiting_captain and two.alerted_at is not None
    assert four.reply_status == ReplyStatus.skipped and four.ai_reply == "Thanks Fay!"
    alerts = (
        await db_session.execute(
            select(Notification).where(
                Notification.client_id == temp_client.client_id, Notification.kind == "low_star_review"
            )
        )
    ).scalars().all()
    assert len(alerts) == 1

    # Not due yet → nothing posted; once due → posted (dev) and auto_sent
    await post_due_review_replies(db_session, settings)
    assert five.reply_posted_at is None
    await post_due_review_replies(db_session, settings, now=datetime.now(UTC) + timedelta(hours=25))
    assert five.reply_posted_at is not None and five.reply_status == ReplyStatus.auto_sent
    await db_session.commit()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_yelp_reply_flagged_manual(db_session, settings, temp_client) -> None:
    temp_client.auto_reply_delay_hours = 0
    await ingest_reviews(
        db_session, settings, temp_client, ReviewProvider.yelp,
        [rp.FetchedReview("y5", 5, "Great", "Gil", datetime.now(UTC))],
    )
    await post_due_review_replies(db_session, settings, now=datetime.now(UTC) + timedelta(minutes=1))
    review = (
        await db_session.execute(select(Review).where(Review.client_id == temp_client.client_id))
    ).scalar_one()
    assert review.reply_posted_at is None
    assert review.generation_meta["needs_manual_reply"] is True
    assert "no reply API" in review.reply_error
    await db_session.commit()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_google_reply_posted_live(db_session, settings, temp_client, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if "oauth2.googleapis.com/token" in str(request.url):
            return httpx.Response(200, json={"access_token": "at-1", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer at-1"
        assert json.loads(request.content) == {"comment": "Thank you!"}
        return httpx.Response(200, json={"comment": "Thank you!"})

    _mock_httpx(monkeypatch, handler)
    temp_client.gbp_location_id = "accounts/9/locations/8"
    temp_client.auto_reply_delay_hours = 0
    await put_credential(db_session, settings, temp_client.client_id, "google", {"refresh_token": "rt"})
    review = Review(client_id=temp_client.client_id, provider=ReviewProvider.google, external_id="gx",
                    rating=5, ai_reply="Thank you!", reply_status=ReplyStatus.scheduled,
                    reply_due_at=datetime.now(UTC) - timedelta(minutes=1))
    db_session.add(review)
    await db_session.flush()

    result = await post_due_review_replies(db_session, settings)
    assert result["posted"] >= 1
    assert review.generation_meta["posted_via"] == "google"
    assert ("PUT", "https://mybusiness.googleapis.com/v4/accounts/9/locations/8/reviews/gx/reply") in calls
    await db_session.commit()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_captain_approve_edited_and_skip(client: AsyncClient, db_session, settings, temp_client) -> None:
    await ingest_reviews(
        db_session, settings, temp_client, ReviewProvider.google,
        [rp.FetchedReview("c2", 2, "Rude", "Hal", datetime.now(UTC)),
         rp.FetchedReview("c5", 5, "Wow", "Ivy", datetime.now(UTC))],
    )
    await db_session.commit()
    rows = {
        r.external_id: str(r.review_id)
        for r in (
            await db_session.execute(select(Review).where(Review.client_id == temp_client.client_id))
        ).scalars()
    }
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship/reviews")
    approved = await client.post(
        f"/api/v1/reviews/{rows['c2']}/approve-reply",
        headers=auth_headers(captain),
        json={"reply_text": "Hal, we're sorry — please call us."},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["reply_status"] == "captain_approved"
    assert body["ai_reply"].startswith("Hal, we're sorry")
    assert body["reply_posted_at"]  # dev-posted inline

    skipped = await client.post(f"/api/v1/reviews/{rows['c5']}/skip-reply", headers=auth_headers(captain))
    assert skipped.status_code == 200 and skipped.json()["reply_status"] == "skipped"

    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    cid = str(temp_client.client_id)
    synced = await client.post(f"/api/v1/clients/{cid}/reviews/sync", headers=auth_headers(crew, cid))
    assert synced.status_code == 200 and synced.json()["new"] == 0  # nothing connected


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_google_oauth_start_and_callback(client: AsyncClient, db_session, temp_client, monkeypatch) -> None:
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    cid = str(temp_client.client_id)
    h = auth_headers(crew, cid)
    assert (await client.get(f"/api/v1/clients/{cid}/integrations/google/start", headers=h)).status_code == 400

    live = Settings(google_client_id="gid", google_client_secret="gsecret")
    app.dependency_overrides[get_settings] = lambda: live
    try:
        start = await client.get(f"/api/v1/clients/{cid}/integrations/google/start", headers=h)
        assert start.status_code == 200
        q = parse_qs(urlparse(start.json()["auth_url"]).query)
        assert q["access_type"] == ["offline"] and q["client_id"] == ["gid"]

        bad = await client.get("/api/v1/integrations/google/callback?code=x&state=forged")
        assert bad.status_code == 400

        _mock_httpx(monkeypatch, lambda r: httpx.Response(200, json={"refresh_token": "rt-new"}))
        cb = await client.get(
            f"/api/v1/integrations/google/callback?code=abc&state={q['state'][0]}", follow_redirects=False
        )
        assert cb.status_code == 307
        assert cb.headers["location"].endswith(f"/crew/clients/{cid}?google=connected")
        stored = await get_credential(db_session, live, temp_client.client_id, "google")
        assert stored == {"refresh_token": "rt-new"}
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_performance_upsert_feeds_detailed_view(db_session, temp_client) -> None:
    d = datetime.now(UTC).date()
    await upsert_performance(db_session, temp_client.client_id, {d: {"impressions": 70, "gbp_direction_requests": 4, "clicks": 7}})
    row = (
        await db_session.execute(
            select(DailyRoiMetric).where(DailyRoiMetric.client_id == temp_client.client_id)
        )
    ).scalar_one()
    assert (row.impressions, row.gbp_direction_requests, row.clicks) == (70, 4, 7)
    await db_session.commit()
