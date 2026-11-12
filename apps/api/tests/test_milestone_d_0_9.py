"""Milestone D / 0.9.0: worker, Ayrshare publishing, encrypted credentials, Crew client settings."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import delete, text, update

from app.config import Settings
from app.models import (
    ApprovalStatus,
    ContentQueue,
    IntegrationCredential,
    MediaAsset,
    PlatformChannel,
)
from app.services import publishing
from app.services.credentials import decrypt_payload, encrypt_payload, put_credential
from app.worker import JOBS, run_job
from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    OAK_LAWN_CLIENT_ID,
    SEEDED_ASSET_ID,
    auth_headers,
    sign_in_token,
)

CLIENT_UUID = uuid.UUID(OAK_LAWN_CLIENT_ID)


@pytest.mark.unit
def test_credentials_round_trip_and_wrong_key() -> None:
    a = Settings(credentials_encryption_key="key-a")
    token = encrypt_payload(a, {"profile_key": "PK-123"})
    assert "PK-123" not in token
    assert decrypt_payload(a, token) == {"profile_key": "PK-123"}
    with pytest.raises(ValueError):
        decrypt_payload(Settings(credentials_encryption_key="key-b"), token)


@pytest.mark.unit
def test_ayrshare_body_per_channel() -> None:
    reel = ContentQueue(channel=PlatformChannel.instagram_reel, caption_text="Hi")
    body = publishing.build_ayrshare_body(reel, "https://cdn/x.mp4")
    assert body["platforms"] == ["instagram"]
    assert body["mediaUrls"] == ["https://cdn/x.mp4"]
    assert body["instagramOptions"]["reels"] is True
    gbp = publishing.build_ayrshare_body(
        ContentQueue(channel=PlatformChannel.gbp_update, caption_text="Hi"), None
    )
    assert gbp["platforms"] == ["gmb"] and "mediaUrls" not in gbp


async def _park_other_due_posts(db_session) -> None:
    """Push every pre-existing due post into the future (rolled back with the test) so leftover
    rows in a shared dev DB can't fill the publish batch ahead of the test's own posts (BUG-008)."""
    await db_session.execute(
        update(ContentQueue)
        .where(
            ContentQueue.status == ApprovalStatus.approved,
            ContentQueue.scheduled_publish_at <= datetime.now(UTC),
        )
        .values(scheduled_publish_at=datetime.now(UTC) + timedelta(days=365))
    )


async def _due_post(db_session, channel: PlatformChannel, asset_id=None) -> ContentQueue:
    post = ContentQueue(
        client_id=CLIENT_UUID,
        channel=channel,
        asset_id=asset_id,
        caption_text=f"[0.9 test] {channel.value}",
        scheduled_publish_at=datetime.now(UTC) - timedelta(minutes=1),
        status=ApprovalStatus.approved,
        generation_meta={"test": "0.9"},
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_publish_due_posts_dev_mode(db_session, settings) -> None:
    assert not publishing.publish_live(settings)
    try:
        await _park_other_due_posts(db_session)
        fb = await _due_post(db_session, PlatformChannel.facebook)
        email = await _due_post(db_session, PlatformChannel.email_blast)
        tiktok = await _due_post(db_session, PlatformChannel.tiktok)  # no asset
        future = ContentQueue(
            client_id=CLIENT_UUID,
            channel=PlatformChannel.facebook,
            caption_text="[0.9 test] future",
            scheduled_publish_at=datetime.now(UTC) + timedelta(days=1),
            status=ApprovalStatus.approved,
        )
        db_session.add(future)
        await db_session.flush()

        await publishing.publish_due_posts(db_session, settings)
        assert fb.status == ApprovalStatus.published
        assert fb.published_external_id.startswith("dev-")
        assert email.status == ApprovalStatus.approved
        assert email.generation_meta["needs_manual_publish"] is True
        assert tiktok.status == ApprovalStatus.approved
        assert tiktok.generation_meta["publish_attempts"] == 1
        assert future.status == ApprovalStatus.approved

        for _ in range(settings.publish_max_attempts):
            await publishing.publish_due_posts(db_session, settings)
        assert tiktok.generation_meta["publish_failed"] is True
        assert tiktok.generation_meta["publish_attempts"] == settings.publish_max_attempts
    finally:
        await db_session.rollback()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_publish_live_ayrshare_request(db_session, monkeypatch) -> None:
    live = Settings(ayrshare_api_key="AYR-KEY", credentials_encryption_key="test-key")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success", "id": "ayr-post-1"})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        publishing.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    try:
        await put_credential(db_session, live, CLIENT_UUID, "ayrshare", {"profile_key": "PROFILE-1"})
        await _park_other_due_posts(db_session)
        post = await _due_post(db_session, PlatformChannel.instagram_post, uuid.UUID(SEEDED_ASSET_ID))
        result = await publishing.publish_due_posts(db_session, live)
        assert result["published"] >= 1
        assert post.status == ApprovalStatus.published
        assert post.published_external_id == "ayr-post-1"
        assert seen["headers"]["authorization"] == "Bearer AYR-KEY"
        assert seen["headers"]["profile-key"] == "PROFILE-1"
        assert seen["body"]["platforms"] == ["instagram"]
        asset = await db_session.get(MediaAsset, uuid.UUID(SEEDED_ASSET_ID))
        assert seen["body"]["mediaUrls"] == [asset.storage_url]
    finally:
        await db_session.rollback()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_worker_job_skips_when_lock_held(db_session, settings) -> None:
    job = next(j for j in JOBS if j.name == "expire_overdue_posts")
    await db_session.execute(text("SELECT pg_advisory_lock(:k)"), {"k": job.lock_key})
    try:
        assert await run_job(job, settings) is None
    finally:
        await db_session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": job.lock_key})
    assert await run_job(job, settings) is not None


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_crew_client_settings_and_integrations(client: AsyncClient, db_session) -> None:
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    crew_h = auth_headers(crew, OAK_LAWN_CLIENT_ID)
    base = f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}"

    denied = await client.get(f"{base}/settings", headers=auth_headers(captain, OAK_LAWN_CLIENT_ID))
    assert denied.status_code == 403

    before = (await client.get(f"{base}/settings", headers=crew_h)).json()
    try:
        patched = await client.patch(
            f"{base}/settings", headers=crew_h, json={"billing_anchor_day": 15, "gbp_location_id": "loc-1"}
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["billing_anchor_day"] == 15
        assert patched.json()["average_ticket_value"] == before["average_ticket_value"]
        bad = await client.patch(f"{base}/settings", headers=crew_h, json={"billing_anchor_day": 31})
        assert bad.status_code == 422

        put = await client.put(
            f"{base}/integrations/ayrshare", headers=crew_h, json={"profile_key": "PROFILE-XYZ-123"}
        )
        assert put.status_code == 200, put.text
        listed = await client.get(f"{base}/integrations", headers=crew_h)
        assert any(i["provider"] == "ayrshare" for i in listed.json())
        assert "PROFILE-XYZ-123" not in listed.text
    finally:
        await client.patch(
            f"{base}/settings",
            headers=crew_h,
            json={"billing_anchor_day": before["billing_anchor_day"],
                  "gbp_location_id": before["gbp_location_id"]},
        )
        await db_session.execute(
            delete(IntegrationCredential).where(
                IntegrationCredential.client_id == CLIENT_UUID,
                IntegrationCredential.provider == "ayrshare",
            )
        )
        await db_session.commit()


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_mark_published_and_retry(client: AsyncClient, db_session) -> None:
    email = await _due_post(db_session, PlatformChannel.email_blast)
    email.scheduled_publish_at = datetime.now(UTC) + timedelta(days=2)
    email.generation_meta = {"publish_failed": True, "publish_attempts": 3}
    await db_session.commit()
    try:
        crew = await sign_in_token(client, CREW_PHONE, "/crew")
        retry = await client.post(f"/api/v1/queue/{email.post_id}/publish-retry", headers=auth_headers(crew))
        assert retry.status_code == 200, retry.text
        assert "publish_failed" not in retry.json()["generation_meta"]

        done = await client.post(f"/api/v1/queue/{email.post_id}/mark-published", headers=auth_headers(crew))
        assert done.status_code == 200, done.text
        assert done.json()["status"] == "published"
    finally:
        await db_session.execute(delete(ContentQueue).where(ContentQueue.post_id == email.post_id))
        await db_session.commit()
