"""Milestone D / 1.0.0: PRD §7 pilot KPIs."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models import ContentQueue
from app.services.kpis import client_kpis
from tests.helpers import CAPTAIN_PHONE, CREW_PHONE, auth_headers, sign_in_token


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_time_to_approve_and_activity(client: AsyncClient, db_session, temp_client) -> None:
    cid = str(temp_client.client_id)
    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    gen = await client.post(
        f"/api/v1/clients/{cid}/campaigns/generate",
        headers=auth_headers(crew, cid),
        json={"asset_ids": [], "channels": ["facebook"], "days": 3, "count": 2},
    )
    ids = [p["post_id"] for p in gen.json()]
    await client.post(f"/api/v1/clients/{cid}/queue/release", headers=auth_headers(crew, cid),
                      json={"post_ids": ids})
    # Pretend one batch went out 10h ago and the other 60h ago
    for pid, hours in zip(ids, (10, 60), strict=True):
        await db_session.execute(
            update(ContentQueue).where(ContentQueue.post_id == pid)
            .values(released_at=datetime.now(UTC) - timedelta(hours=hours))
        )
    await db_session.commit()

    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")
    for pid in ids:
        assert (await client.post(f"/api/v1/queue/{pid}/approve", headers=auth_headers(captain))).status_code == 200

    k = await client_kpis(db_session, temp_client)
    assert k["approvals_30d"] == 2
    assert 34 <= k["avg_time_to_approve_hours"] <= 36
    assert k["approved_within_48h_pct"] == 50
    assert k["captain_active_30d"] is True

    res = await client.get("/api/v1/kpis", headers=auth_headers(crew))
    assert res.status_code == 200, res.text
    body = res.json()
    assert any(r["client_id"] == cid for r in body["clients"])
    assert body["summary"]["targets"]["avg_time_to_approve_hours"] == "< 48"
    assert (await client.get("/api/v1/kpis", headers=auth_headers(captain))).status_code == 403
