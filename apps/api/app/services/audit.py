"""Audit log: who changed what, when.

Status transitions of posts (``content_queue.status``) and reviews (``reviews.reply_status``)
are captured automatically by a ``before_flush`` hook, so every path — API, worker jobs,
webhooks — is covered without remembering to log. The actor comes from a context variable
set during authentication; background work records ``system``.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models import AuditEvent, ContentQueue, Review


@dataclass(frozen=True)
class Actor:
    user_id: uuid.UUID | None
    role: str


SYSTEM = Actor(user_id=None, role="system")
current_actor: ContextVar[Actor] = ContextVar("current_actor", default=SYSTEM)


def set_actor(user_id: uuid.UUID | None, role: str) -> None:
    current_actor.set(Actor(user_id=user_id, role=role))


def _value(v: object) -> str | None:
    if v is None:
        return None
    return getattr(v, "value", str(v))


def record(
    session: Session,
    *,
    client_id: uuid.UUID | None,
    entity_type: str,
    entity_id: object,
    action: str,
    from_status: object = None,
    to_status: object = None,
    details: dict | None = None,
    actor: Actor | None = None,
) -> None:
    actor = actor or current_actor.get()
    session.add(
        AuditEvent(
            client_id=client_id,
            actor_user_id=actor.user_id,
            actor_role=actor.role,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            action=action,
            from_status=_value(from_status),
            to_status=_value(to_status),
            details=details,
        )
    )


TRACKED = {ContentQueue: ("post", "status", "post_id"), Review: ("review", "reply_status", "review_id")}


@event.listens_for(Session, "before_flush")
def _capture_status_changes(session: Session, _ctx, _instances) -> None:
    for obj in list(session.new) + list(session.dirty):
        spec = TRACKED.get(type(obj))
        if spec is None:
            continue
        entity_type, attr, pk = spec
        hist = inspect(obj).attrs[attr].history
        if obj in session.new:
            before, after = None, getattr(obj, attr)
            if after is None:
                continue
        elif hist.has_changes():
            before = hist.deleted[0] if hist.deleted else None
            after = hist.added[0] if hist.added else None
            if _value(before) == _value(after):
                continue
        else:
            continue
        if getattr(obj, pk) is None:
            setattr(obj, pk, uuid.uuid4())  # PK default fires on INSERT; we need it now
        record(
            session,
            client_id=obj.client_id,
            entity_type=entity_type,
            entity_id=getattr(obj, pk),
            action="created" if obj in session.new else "status_change",
            from_status=before,
            to_status=after,
        )
