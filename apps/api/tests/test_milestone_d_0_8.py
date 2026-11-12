"""Milestone D / 0.8.0: notifications, 48h queue deep link, expiry + reminders, low-star alert."""

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.config import Settings
from app.models import (
    ApprovalStatus,
    AuthMagicLink,
    ContentQueue,
    Notification,
    PlatformChannel,
    Review,
    ReviewProvider,
)
from app.services import sms as sms_service
from app.services.auth import hash_token
from app.services.jobs import expire_overdue_posts, send_expiry_reminders
from app.services.reviews import ensure_ai_reply
from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    OAK_LAWN_CLIENT_ID,
    auth_headers,
    sign_in_token,
)

CLIENT_UUID = uuid.UUID(OAK_LAWN_CLIENT_ID)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_sms_is_async_httpx(monkeypatch) -> None:
    """BUG-002: SMS goes through httpx.AsyncClient (non-blocking), with Twilio's form fields."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = parse_qs(request.content.decode())
        return httpx.Response(201, json={"sid": "SM123"})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        sms_service.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    settings = Settings(
        auth_dev_mode=False,
        twilio_account_sid="AC1",
        twilio_auth_token="tok",
        twilio_from_number="+15550000000",
    )
    assert sms_service.sms_enabled(settings)
    sid = await sms_service.send_sms(settings, to="+15551234001", body="hi")
    assert sid == "SM123"
    assert seen["url"].endswith("/Accounts/AC1/Messages.json")
    assert seen["body"]["To"] == ["+15551234001"]
    assert seen["body"]["From"] == ["+15550000000"]


@pytest.mark.unit
def test_sms_disabled_in_dev() -> None:
    assert not sms_service.sms_enabled(Settings(auth_dev_mode=True, twilio_account_sid="AC1",
                                                twilio_auth_token="t", twilio_from_number="+1"))
    assert not sms_service.sms_enabled(Settings(auth_dev_mode=False))


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_release_sends_queue_ready_with_48h_deep_link(client: AsyncClient, db_session) -> None:
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    crew_h = auth_headers(crew, OAK_LAWN_CLIENT_ID)
    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_h,
        json={"asset_ids": [], "channels": ["facebook"], "days": 5, "count": 1},
    )
    post_id = gen.json()[0]["post_id"]
    rel = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_h,
        json={"post_ids": [post_id]},
    )
    assert rel.status_code == 200, rel.text
    last = rel.json()[0]["generation_meta"]["last_notify"]
    assert last["type"] == "queue_ready"
    assert last["channel"] == "log"  # dev: no FCM, no live Twilio

    note = (
        await db_session.execute(
            select(Notification).where(
                Notification.notification_id == uuid.UUID(last["notification_id"])
            )
        )
    ).scalar_one()
    link = note.payload["dev_magic_link"]
    assert link and link in note.body

    raw = parse_qs(urlparse(link).query)["token"][0]
    stored = (
        await db_session.execute(
            select(AuthMagicLink).where(AuthMagicLink.token_hash == hash_token(raw))
        )
    ).scalar_one()
    ttl = stored.expires_at - datetime.now(UTC)
    assert timedelta(hours=47) < ttl <= timedelta(hours=48)

    # Story 1.1: tapping the link signs the Captain straight into the approval queue
    verified = await client.get(f"/api/v1/auth/verify?token={raw}")
    assert verified.status_code == 200, verified.text
    assert verified.json()["redirect_path"] == "/ship/posts?tab=pending"
    assert verified.json()["user"]["role"] == "captain"

    # Crew can see the delivery log
    feed = await client.get(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/notifications", headers=crew_h
    )
    assert feed.status_code == 200
    assert any(n["notification_id"] == last["notification_id"] for n in feed.json())


async def _make_post(db_session, *, publish_in: timedelta, released_ago: timedelta) -> ContentQueue:
    now = datetime.now(UTC)
    post = ContentQueue(
        client_id=CLIENT_UUID,
        channel=PlatformChannel.facebook,
        caption_text="[0.8 test] expiry",
        scheduled_publish_at=now + publish_in,
        status=ApprovalStatus.pending_client,
        released_at=now - released_ago,
        generation_meta={"test": "0.8"},
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_expiry_reminder_once_per_client(db_session, settings) -> None:
    try:
        # Isolate from other pending posts left by earlier tests
        await db_session.execute(
            ContentQueue.__table__.update()
            .where(ContentQueue.status == ApprovalStatus.pending_client)
            .values(reminder_sent_at=datetime.now(UTC))
        )
        soon = await _make_post(db_session, publish_in=timedelta(hours=20), released_ago=timedelta(hours=5))
        also = await _make_post(db_session, publish_in=timedelta(hours=40), released_ago=timedelta(hours=5))
        later = await _make_post(db_session, publish_in=timedelta(days=5), released_ago=timedelta(hours=5))
        fresh = await _make_post(db_session, publish_in=timedelta(hours=10), released_ago=timedelta(minutes=5))

        results = await send_expiry_reminders(db_session, settings)
        assert len(results) == 1
        assert results[0]["posts"] == 2
        assert results[0]["type"] == "queue_expiring"
        assert soon.reminder_sent_at and also.reminder_sent_at
        assert later.reminder_sent_at is None  # outside the 48h window
        assert fresh.reminder_sent_at is None  # just released; queue_ready covers it

        assert await send_expiry_reminders(db_session, settings) == []
    finally:
        await db_session.rollback()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_expire_then_crew_reschedules(client: AsyncClient, db_session) -> None:
    post = await _make_post(db_session, publish_in=timedelta(hours=-1), released_ago=timedelta(days=3))
    await db_session.commit()
    try:
        assert await expire_overdue_posts(db_session) >= 1
        await db_session.commit()
        await db_session.refresh(post)
        assert post.status == ApprovalStatus.expired

        crew = await sign_in_token(client, CREW_PHONE, "/crew")
        captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
        cant = await client.post(f"/api/v1/queue/{post.post_id}/approve", headers=auth_headers(captain))
        assert cant.status_code == 400

        needs_time = await client.put(
            f"/api/v1/queue/{post.post_id}/caption",
            headers=auth_headers(crew),
            json={"caption_text": "Rescheduled"},
        )
        assert needs_time.status_code == 400

        new_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        ok = await client.put(
            f"/api/v1/queue/{post.post_id}/caption",
            headers=auth_headers(crew),
            json={"caption_text": "Rescheduled", "scheduled_publish_at": new_time},
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "pending_client"
    finally:
        await db_session.execute(delete(ContentQueue).where(ContentQueue.post_id == post.post_id))
        await db_session.commit()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_bug003_low_star_alert_fires_once(db_session, settings) -> None:
    review = Review(
        client_id=CLIENT_UUID,
        provider=ReviewProvider.google,
        external_id=f"bug003-{uuid.uuid4()}",
        rating=2,
        body="Long wait.",
        reviewer_name="Test R.",
        reviewed_at=datetime.now(UTC),
    )
    db_session.add(review)
    await db_session.flush()
    try:
        await ensure_ai_reply(db_session, settings, review)
        assert review.reply_status.value == "awaiting_captain"
        assert review.alerted_at is not None
        alerts = (
            await db_session.execute(
                select(Notification).where(
                    Notification.kind == "low_star_review",
                    Notification.payload["review_id"].astext == str(review.review_id),
                )
            )
        ).scalars().all()
        assert len(alerts) == 1
        assert "Draft reply ready" in alerts[0].body

        await ensure_ai_reply(db_session, settings, review)  # second pass: no duplicate
        again = (
            await db_session.execute(
                select(Notification).where(
                    Notification.payload["review_id"].astext == str(review.review_id)
                )
            )
        ).scalars().all()
        assert len(again) == 1
    finally:
        await db_session.rollback()
