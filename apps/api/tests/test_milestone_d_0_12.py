"""Milestone D / 0.12.0: voice-note edit requests (Story 1.2)."""

import pytest
from httpx import AsyncClient

from tests.helpers import (
    CAPTAIN_PHONE,
    CREW_PHONE,
    OAK_LAWN_CLIENT_ID,
    auth_headers,
    sign_in_token,
)


async def _pending_post(client: AsyncClient) -> str:
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    crew_h = auth_headers(crew, OAK_LAWN_CLIENT_ID)
    gen = await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/campaigns/generate",
        headers=crew_h,
        json={"asset_ids": [], "channels": ["facebook"], "days": 5, "count": 1},
    )
    post_id = gen.json()[0]["post_id"]
    await client.post(
        f"/api/v1/clients/{OAK_LAWN_CLIENT_ID}/queue/release",
        headers=crew_h,
        json={"post_ids": [post_id]},
    )
    return post_id


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_voice_note_request_edit(client: AsyncClient, settings) -> None:
    assert settings.llm_dev_mode is True
    post_id = await _pending_post(client)
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship/posts")

    res = await client.post(
        f"/api/v1/queue/{post_id}/request-edit-voice",
        headers=auth_headers(captain),
        files={"audio": ("note.webm", b"\x1aE\xdf\xa3fake-webm-bytes", "audio/webm")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "pending_client"  # dev transcript → AI rewrite
    assert body["voice_feedback_url"].endswith(".webm")
    assert body["client_feedback"].startswith("[DEV voice note]")
    assert body["caption_text"].startswith("[DEV revised]")
    assert body["generation_meta"]["transcription"]["mode"] == "dev"

    # The stored note is served back for Crew to listen to
    path = body["voice_feedback_url"].split("/uploads/", 1)[1]
    served = await client.get(f"/uploads/{path}")
    assert served.status_code == 200 and served.content.startswith(b"\x1aE\xdf\xa3")


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_voice_note_validation_and_roles(client: AsyncClient) -> None:
    post_id = await _pending_post(client)
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship/posts")
    crew = await sign_in_token(client, CREW_PHONE, "/crew")

    wrong_type = await client.post(
        f"/api/v1/queue/{post_id}/request-edit-voice",
        headers=auth_headers(captain),
        files={"audio": ("note.txt", b"hello", "text/plain")},
    )
    assert wrong_type.status_code == 415

    too_big = await client.post(
        f"/api/v1/queue/{post_id}/request-edit-voice",
        headers=auth_headers(captain),
        files={"audio": ("note.webm", b"0" * (2 * 1024 * 1024 + 1), "audio/webm")},
    )
    assert too_big.status_code == 413

    crew_denied = await client.post(
        f"/api/v1/queue/{post_id}/request-edit-voice",
        headers=auth_headers(crew),
        files={"audio": ("note.webm", b"abc", "audio/webm")},
    )
    assert crew_denied.status_code == 403
