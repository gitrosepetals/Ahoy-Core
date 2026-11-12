"""Milestone D / 0.14.0: Captain-facing messages use the Ship's vocabulary (Captain / Ship / Crew)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Notification
from app.services.notify import (
    notify_captain_low_star_review,
    notify_captain_queue_expiring,
    notify_captain_queue_ready,
)


@pytest.mark.milestone_d
@pytest.mark.asyncio
async def test_captain_notifications_are_on_theme(db_session, settings, temp_client) -> None:
    cid = temp_client.client_id
    await notify_captain_queue_ready(db_session, settings, client_id=cid, post_count=3)
    await notify_captain_queue_expiring(
        db_session, settings, client_id=cid, post_count=2,
        first_deadline=datetime.now(UTC) + timedelta(days=1),
    )
    await notify_captain_low_star_review(
        db_session, settings, client_id=cid, rating=2, review_id=uuid.uuid4(),
        reviewer_name="Jo", draft_reply="Sorry Jo",
    )
    notes = (
        await db_session.execute(select(Notification).where(Notification.client_id == cid))
    ).scalars().all()
    assert len(notes) == 3
    for note in notes:
        assert "Captain" in note.body, note.body
        for off_theme in ("owner", "your OK"):
            assert off_theme not in note.body, note.body
    ready = next(n for n in notes if n.kind == "queue_ready")
    assert "Manifest" in ready.body
    await db_session.rollback()
