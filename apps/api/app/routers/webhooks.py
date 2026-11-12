"""Inbound webhooks: Twilio call tracking (TwiML) and website lead forms."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from xml.sax.saxutils import escape, quoteattr

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.deps import AppSettings, DbSession
from app.models import Client, LeadEvent, LeadEventType
from app.services import twilio_sig
from app.services.leads import record_form_lead, upsert_call_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

RECORDING_NOTICE = "This call may be recorded for quality and training."
FORM_FIELDS = ("name", "email", "phone", "message", "service", "page")
MAX_FIELD_LEN = 2000


def _twiml(body: str = "") -> Response:
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>',
        media_type="application/xml",
    )


async def _twilio_params(request: Request, settings) -> dict[str, str]:
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    public_url = settings.public_api_base_url.rstrip("/") + request.url.path
    if request.url.query:
        public_url += f"?{request.url.query}"
    if not twilio_sig.is_valid(
        settings,
        url=public_url,
        params=params,
        signature=request.headers.get("X-Twilio-Signature"),
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bad Twilio signature")
    return params


async def _client_for_number(db, number: str | None) -> Client | None:
    if not number:
        return None
    return (
        await db.execute(select(Client).where(Client.twilio_tracking_number == number))
    ).scalar_one_or_none()


@router.post("/twilio/voice")
async def twilio_voice_incoming(request: Request, db: DbSession, settings: AppSettings) -> Response:
    """Voice URL of each tracking number: forward to the business, optionally recording."""
    params = await _twilio_params(request, settings)
    client = await _client_for_number(db, params.get("To"))
    if client is None or not client.forward_to_number:
        logger.warning("Tracking call to unknown/unconfigured number %s", params.get("To"))
        return _twiml("<Say>Sorry, this number is not in service.</Say><Hangup/>")

    await upsert_call_event(
        db,
        client_id=client.client_id,
        call_sid=params.get("CallSid", ""),
        duration_seconds=None,
        meta={"from": params.get("From"), "to": params.get("To"), "status": "ringing",
              "caller_city": params.get("FromCity"), "caller_state": params.get("FromState")},
    )
    await db.commit()

    base = settings.public_api_base_url.rstrip("/") + settings.api_prefix + "/webhooks/twilio"
    attrs = f' action={quoteattr(base + "/voice/complete")} timeout="25"'
    say = ""
    if client.record_calls:
        attrs += (
            ' record="record-from-answer-dual"'
            f' recordingStatusCallback={quoteattr(base + "/recording")}'
        )
        say = f"<Say>{escape(RECORDING_NOTICE)}</Say>"
    return _twiml(f"{say}<Dial{attrs}><Number>{escape(client.forward_to_number)}</Number></Dial>")


@router.post("/twilio/voice/complete")
async def twilio_voice_complete(request: Request, db: DbSession, settings: AppSettings) -> Response:
    """<Dial action>: the forwarded call ended — store talk time (qualification uses it)."""
    params = await _twilio_params(request, settings)
    client = await _client_for_number(db, params.get("To"))
    if client is not None:
        duration = params.get("DialCallDuration")
        await upsert_call_event(
            db,
            client_id=client.client_id,
            call_sid=params.get("CallSid", ""),
            duration_seconds=int(duration) if duration and duration.isdigit() else 0,
            meta={"status": params.get("DialCallStatus"), "recording_url": params.get("RecordingUrl"),
                  "completed_at": datetime.now(UTC).isoformat()},
        )
        await db.commit()
    return _twiml()


@router.post("/twilio/recording", status_code=status.HTTP_204_NO_CONTENT)
async def twilio_recording_status(request: Request, db: DbSession, settings: AppSettings) -> None:
    params = await _twilio_params(request, settings)
    if params.get("RecordingStatus") not in (None, "completed"):
        return
    event = (
        await db.execute(
            select(LeadEvent).where(
                LeadEvent.event_type == LeadEventType.tracked_call,
                LeadEvent.external_id == params.get("CallSid"),
            )
        )
    ).scalar_one_or_none()
    if event is not None and params.get("RecordingUrl"):
        event.meta = {**(event.meta or {}), "recording_url": params["RecordingUrl"]}
        await db.commit()


@router.post("/forms/{form_key}")
async def website_form_lead(form_key: str, request: Request, db: DbSession) -> Response:
    """Public endpoint for a client's website form (HTML form POST or JSON / Zapier).

    Optional ``_redirect`` (thank-you page) and ``_gotcha`` honeypot fields.
    """
    client = (
        await db.execute(select(Client).where(Client.lead_form_key == form_key))
    ).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Unknown form")

    if request.headers.get("content-type", "").startswith("application/json"):
        raw = await request.json()
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail="Expected a JSON object")
    else:
        raw = dict(await request.form())
    data = {k: str(v)[:MAX_FIELD_LEN] for k, v in raw.items() if v is not None}

    redirect = data.pop("_redirect", None)
    if not data.pop("_gotcha", ""):  # bots fill the hidden honeypot; drop silently
        fields = {k: data[k] for k in FORM_FIELDS if data.get(k)}
        extra = {k: v for k, v in data.items() if k not in FORM_FIELDS and not k.startswith("_")}
        if extra:
            fields["extra"] = dict(list(extra.items())[:20])
        if not (fields.get("email") or fields.get("phone")):
            raise HTTPException(status_code=422, detail="Provide an email or phone")
        await record_form_lead(db, client_id=client.client_id, fields=fields)
        await db.commit()

    if redirect and redirect.startswith(("https://", "http://")):
        return RedirectResponse(redirect, status_code=status.HTTP_303_SEE_OTHER)
    return JSONResponse({"ok": True})
