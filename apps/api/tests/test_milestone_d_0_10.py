"""Milestone D / 0.10.0: Twilio call tracking, form leads, rollup, itemized leads, Detailed View."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import Settings, get_settings
from app.main import app
from app.models import DailyRoiMetric, LeadEvent, LeadEventType
from app.services import twilio_sig
from app.services.leads import is_qualified_call, rollup_client_days
from tests.helpers import CAPTAIN_PHONE, CREW_PHONE, auth_headers, sign_in_token

TZ = "America/Chicago"


@pytest.mark.unit
def test_qualified_call_threshold() -> None:
    assert not is_qualified_call(None)
    assert not is_qualified_call(59)
    assert is_qualified_call(60)


@pytest.mark.unit
def test_twilio_signature_round_trip() -> None:
    settings = Settings(twilio_auth_token="secret", auth_dev_mode=False)
    params = {"CallSid": "CA1", "To": "+15550001111", "From": "+15559990000"}
    url = "https://api.example.com/api/v1/webhooks/twilio/voice"
    sig = twilio_sig.compute_signature("secret", url, params)
    assert twilio_sig.is_valid(settings, url=url, params=params, signature=sig)
    assert not twilio_sig.is_valid(settings, url=url, params={**params, "To": "+1"}, signature=sig)
    assert not twilio_sig.is_valid(settings, url=url, params=params, signature=None)
    # dev mode: not enforced
    assert twilio_sig.is_valid(Settings(auth_dev_mode=True), url=url, params=params, signature=None)


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_call_tracking_webhooks_and_rollup(client: AsyncClient, db_session, temp_client) -> None:
    tracking = temp_client.twilio_tracking_number
    for sid, talk in (("CA-long", "75"), ("CA-short", "30")):
        incoming = await client.post(
            "/api/v1/webhooks/twilio/voice",
            data={"CallSid": sid, "To": tracking, "From": "+15550009999"},
        )
        assert incoming.status_code == 200, incoming.text
        xml = incoming.text
        assert "<Dial" in xml and "+15557654321" in xml
        assert "may be recorded" in xml and 'record="record-from-answer-dual"' in xml

        done = await client.post(
            "/api/v1/webhooks/twilio/voice/complete",
            data={"CallSid": sid, "To": tracking, "DialCallStatus": "completed",
                  "DialCallDuration": talk,
                  "RecordingUrl": f"https://api.twilio.com/2010-04-01/Accounts/AC/Recordings/RE{sid}"},
        )
        assert done.status_code == 200
        # Twilio retry of the same callback must not create a second event
        await client.post(
            "/api/v1/webhooks/twilio/voice/complete",
            data={"CallSid": sid, "To": tracking, "DialCallStatus": "completed", "DialCallDuration": talk},
        )

    events = (
        await db_session.execute(select(LeadEvent).where(LeadEvent.client_id == temp_client.client_id))
    ).scalars().all()
    assert len(events) == 2
    assert {e.duration_seconds for e in events} == {75, 30}
    assert all(e.meta.get("recording_url") for e in events)

    today = datetime.now(ZoneInfo(TZ)).date()
    await rollup_client_days(db_session, temp_client, start=today, end=today)
    await db_session.commit()
    row = (
        await db_session.execute(
            select(DailyRoiMetric).where(
                DailyRoiMetric.client_id == temp_client.client_id, DailyRoiMetric.metric_date == today
            )
        )
    ).scalar_one()
    assert row.tracked_calls_count == 1  # only the 75s call qualifies

    unknown = await client.post(
        "/api/v1/webhooks/twilio/voice", data={"CallSid": "CA-x", "To": "+19999999999"}
    )
    assert "not in service" in unknown.text


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_twilio_signature_enforced_when_live(client: AsyncClient, temp_client) -> None:
    live = Settings(twilio_auth_token="tok", auth_dev_mode=False)
    app.dependency_overrides[get_settings] = lambda: live
    try:
        res = await client.post(
            "/api/v1/webhooks/twilio/voice",
            data={"CallSid": "CA-sig", "To": temp_client.twilio_tracking_number},
        )
        assert res.status_code == 403
        params = {"CallSid": "CA-sig", "To": temp_client.twilio_tracking_number}
        url = live.public_api_base_url.rstrip("/") + "/api/v1/webhooks/twilio/voice"
        ok = await client.post(
            "/api/v1/webhooks/twilio/voice",
            data=params,
            headers={"X-Twilio-Signature": twilio_sig.compute_signature("tok", url, params)},
        )
        assert ok.status_code == 200, ok.text
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_form_lead_endpoint(client: AsyncClient, db_session, temp_client) -> None:
    url = f"/api/v1/webhooks/forms/{temp_client.lead_form_key}"
    ok = await client.post(url, json={"name": "Pat", "email": "pat@example.com", "message": "Exam?"})
    assert ok.status_code == 200 and ok.json() == {"ok": True}

    redirect = await client.post(
        url, data={"name": "Sam", "phone": "+15551112222", "_redirect": "https://example.com/thanks"}
    )
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "https://example.com/thanks"

    bot = await client.post(url, data={"email": "bot@spam.example", "_gotcha": "x"})
    assert bot.status_code == 200
    assert (await client.post(url, json={"name": "No contact"})).status_code == 422
    assert (await client.post("/api/v1/webhooks/forms/nope", json={"email": "a@b.co"})).status_code == 404

    forms = (
        await db_session.execute(
            select(LeadEvent).where(
                LeadEvent.client_id == temp_client.client_id,
                LeadEvent.event_type == LeadEventType.form_lead,
            )
        )
    ).scalars().all()
    assert sorted(e.meta.get("name") for e in forms) == ["Pat", "Sam"]


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_itemized_leads_and_detailed_view(client: AsyncClient, db_session, temp_client) -> None:
    cid = str(temp_client.client_id)
    db_session.add_all(
        [
            LeadEvent(client_id=temp_client.client_id, event_type=LeadEventType.tracked_call,
                      external_id="CA-item", duration_seconds=120,
                      meta={"from": "+15550001234", "status": "completed",
                            "recording_url": "https://api.twilio.com/x"},
                      occurred_at=datetime.now(UTC) - timedelta(minutes=5)),
            LeadEvent(client_id=temp_client.client_id, event_type=LeadEventType.form_lead,
                      meta={"name": "Lee", "email": "lee@example.com"}, occurred_at=datetime.now(UTC)),
        ]
    )
    await db_session.commit()

    captain = await sign_in_token(client, CAPTAIN_PHONE, "/ship")  # after client exists → in scope
    leads = await client.get(f"/api/v1/clients/{cid}/roi/leads", headers=auth_headers(captain, cid))
    assert leads.status_code == 200, leads.text
    body = leads.json()
    assert [e["event_type"] for e in body] == ["form_lead", "tracked_call"]
    call = body[1]
    assert call["qualified"] is True and call["caller"] == "+15550001234" and call["has_recording"]
    assert body[0]["name"] == "Lee"

    crew = await sign_in_token(client, CREW_PHONE, "/crew")
    today = datetime.now(ZoneInfo(TZ)).date().isoformat()
    denied = await client.put(
        f"/api/v1/clients/{cid}/roi/manual", headers=auth_headers(captain, cid),
        json={"metric_date": today, "impressions": 1000},
    )
    assert denied.status_code == 403
    manual = await client.put(
        f"/api/v1/clients/{cid}/roi/manual", headers=auth_headers(crew, cid),
        json={"metric_date": today, "impressions": 1000, "clicks": 25, "ad_spend_usd": 40},
    )
    assert manual.status_code == 200, manual.text

    roi = (await client.get(f"/api/v1/clients/{cid}/roi", headers=auth_headers(captain, cid))).json()
    assert roi["total_ad_spend_usd"] == 40.0
    assert roi["detail"]["impressions"] == 1000
    assert roi["detail"]["ctr"] == 0.025
