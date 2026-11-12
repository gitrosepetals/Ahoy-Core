"""Milestone D / 0.15.0: audit log attribution + structured logging."""

import json
import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import AuditEvent
from app.observability import JsonFormatter
from app.services.credentials import put_credential
from app.services.jobs import expire_overdue_posts  # noqa: F401  (imports audit hook in worker path)
from tests.helpers import CAPTAIN_PHONE, CREW_PHONE, auth_headers, sign_in_token

CAPTAIN_USER_ID = "11111111-1111-1111-1111-111111111111"
CREW_USER_ID = "22222222-2222-2222-2222-222222222222"


@pytest.mark.unit
def test_json_log_formatter() -> None:
    record = logging.LogRecord("ahoy.test", logging.INFO, __file__, 1, "hello %s", ("Captain",), None)
    line = json.loads(JsonFormatter().format(record))
    assert line["msg"] == "hello Captain" and line["level"] == "INFO" and line["logger"] == "ahoy.test"


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_post_lifecycle_is_audited_with_actors(client: AsyncClient, db_session, temp_client) -> None:
    cid = str(temp_client.client_id)
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")

    gen = await client.post(
        f"/api/v1/clients/{cid}/campaigns/generate",
        headers=auth_headers(crew, cid),
        json={"asset_ids": [], "channels": ["facebook"], "days": 3, "count": 1},
    )
    post_id = gen.json()[0]["post_id"]
    await client.post(f"/api/v1/clients/{cid}/queue/release", headers=auth_headers(crew, cid),
                      json={"post_ids": [post_id]})
    approve = await client.post(f"/api/v1/queue/{post_id}/approve", headers=auth_headers(captain))
    assert approve.status_code == 200

    events = (
        await db_session.execute(
            select(AuditEvent).where(AuditEvent.entity_id == post_id).order_by(AuditEvent.created_at)
        )
    ).scalars().all()
    trail = [(e.action, e.from_status, e.to_status, e.actor_role, str(e.actor_user_id)) for e in events]
    assert trail == [
        ("created", None, "draft_internal", "crew", CREW_USER_ID),
        ("status_change", "draft_internal", "pending_client", "crew", CREW_USER_ID),
        ("status_change", "pending_client", "approved", "captain", CAPTAIN_USER_ID),
    ]

    feed = await client.get(f"/api/v1/clients/{cid}/audit", headers=auth_headers(crew, cid))
    assert feed.status_code == 200
    assert feed.json()[0]["to_status"] == "approved"
    denied = await client.get(f"/api/v1/clients/{cid}/audit", headers=auth_headers(captain, cid))
    assert denied.status_code == 403


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_system_and_credential_audit(db_session, settings, temp_client) -> None:
    await put_credential(db_session, settings, temp_client.client_id, "ayrshare", {"profile_key": "SECRET-123"})
    await db_session.flush()
    cred = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.client_id == temp_client.client_id, AuditEvent.entity_type == "integration"
            )
        )
    ).scalar_one()
    assert cred.action == "credential_saved" and cred.details == {"fields": ["profile_key"]}
    assert "SECRET-123" not in json.dumps(cred.details)
    assert cred.actor_role in ("system", "crew", "captain")  # context default outside a request
    assert uuid.UUID(str(temp_client.client_id))
    await db_session.rollback()
