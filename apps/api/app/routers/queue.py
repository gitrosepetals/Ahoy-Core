import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select

from app.deps import (
    AppSettings,
    CaptainUser,
    CrewUser,
    DbSession,
    TenantClientId,
    require_roles,
)
from app.models import ApprovalStatus, ContentQueue, MediaAsset, UserRole
from app.schemas import (
    AuthUser,
    ContentQueueOut,
    CrewCaptionEditBody,
    QueueReleaseRequest,
    RequestEditBody,
    SwapAssetBody,
)
from app.services.campaigns import crew_edit_caption, rewrite_post_from_feedback
from app.services.llm import transcribe_audio
from app.services.notify import notify_captain_queue_ready
from app.services.storage import StorageError, save_file

router = APIRouter(tags=["queue"])

MAX_VOICE_BYTES = 2 * 1024 * 1024  # ~60s of Opus/WebM; the Ship records up to 30s
VOICE_SUFFIXES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/mpeg": ".mp3",
                  "audio/wav": ".wav", "audio/x-m4a": ".m4a"}


def _post_out(post: ContentQueue) -> ContentQueueOut:
    return ContentQueueOut(
        post_id=post.post_id,
        client_id=post.client_id,
        asset_id=post.asset_id,
        channel=post.channel,
        caption_text=post.caption_text,
        scheduled_publish_at=post.scheduled_publish_at,
        status=post.status,
        client_feedback=post.client_feedback,
        voice_feedback_url=post.voice_feedback_url,
        generation_meta=post.generation_meta,
        created_at=post.created_at,
    )


@router.get("/clients/{client_id}/queue", response_model=list[ContentQueueOut])
async def list_queue(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = Depends(require_roles(UserRole.crew, UserRole.captain)),
    status_filter: ApprovalStatus | None = Query(default=None, alias="status"),
) -> list[ContentQueueOut]:
    stmt = select(ContentQueue).where(ContentQueue.client_id == client_id)
    if status_filter is not None:
        stmt = stmt.where(ContentQueue.status == status_filter)
    stmt = stmt.order_by(ContentQueue.scheduled_publish_at.asc())
    result = await db.execute(stmt)
    return [_post_out(p) for p in result.scalars().all()]


@router.post("/clients/{client_id}/queue/release", response_model=list[ContentQueueOut])
async def release_queue(
    client_id: TenantClientId,
    body: QueueReleaseRequest,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> list[ContentQueueOut]:
    stmt = select(ContentQueue).where(
        ContentQueue.client_id == client_id,
        ContentQueue.status == ApprovalStatus.draft_internal,
    )
    if body.post_ids:
        stmt = stmt.where(ContentQueue.post_id.in_(body.post_ids))
    result = await db.execute(stmt)
    posts = list(result.scalars().all())
    if not posts:
        raise HTTPException(status_code=404, detail="No draft_internal posts to release")

    now = datetime.now(UTC)
    for post in posts:
        post.status = ApprovalStatus.pending_client
        post.released_at = now
        post.reminder_sent_at = None

    notify = await notify_captain_queue_ready(
        db, settings, client_id=client_id, post_count=len(posts)
    )
    await db.commit()
    for post in posts:
        await db.refresh(post)
        meta = dict(post.generation_meta or {})
        meta["last_notify"] = notify
        post.generation_meta = meta
    await db.commit()
    for post in posts:
        await db.refresh(post)
    return [_post_out(p) for p in posts]


async def _load_queue_post(
    db: DbSession,
    post_id: uuid.UUID,
    user: AuthUser,
) -> ContentQueue:
    result = await db.execute(select(ContentQueue).where(ContentQueue.post_id == post_id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if user.role != UserRole.admin and post.client_id not in user.client_ids:
        raise HTTPException(status_code=403, detail="Client out of scope")
    return post


@router.post("/queue/{post_id}/approve", response_model=ContentQueueOut)
async def approve_post(
    post_id: uuid.UUID,
    db: DbSession,
    captain: CaptainUser,
) -> ContentQueueOut:
    post = await _load_queue_post(db, post_id, captain)
    if post.status not in (ApprovalStatus.pending_client, ApprovalStatus.changes_requested):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve post in status {post.status.value}",
        )
    post.status = ApprovalStatus.approved
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.post("/queue/{post_id}/request-edit", response_model=ContentQueueOut)
async def request_edit(
    post_id: uuid.UUID,
    body: RequestEditBody,
    db: DbSession,
    settings: AppSettings,
    captain: CaptainUser,
) -> ContentQueueOut:
    post = await _load_queue_post(db, post_id, captain)
    if post.status not in (ApprovalStatus.pending_client, ApprovalStatus.changes_requested):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot request edit for status {post.status.value}",
        )
    post = await rewrite_post_from_feedback(db, settings, post, body.feedback)
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.post("/queue/{post_id}/request-edit-voice", response_model=ContentQueueOut)
async def request_edit_voice(
    post_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    captain: CaptainUser,
    audio: UploadFile = File(...),
) -> ContentQueueOut:
    """Story 1.2: a short voice note instead of typing. Transcribed, then same loop as text."""
    post = await _load_queue_post(db, post_id, captain)
    if post.status not in (ApprovalStatus.pending_client, ApprovalStatus.changes_requested):
        raise HTTPException(status_code=400, detail=f"Cannot request edit for status {post.status.value}")
    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    if content_type not in VOICE_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported audio type")
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty recording")
    if len(data) > MAX_VOICE_BYTES:
        raise HTTPException(status_code=413, detail="Voice note too long (max ~60 seconds)")

    voice_name = f"{uuid.uuid4()}{VOICE_SUFFIXES[content_type]}"
    try:
        post.voice_feedback_url = await save_file(
            settings,
            key=f"{post.client_id}/voice/{voice_name}",
            data=data,
            content_type=content_type,
        )
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    transcript, meta = await transcribe_audio(
        settings, data=data, filename=voice_name, content_type=content_type
    )
    if transcript is None:
        # Can't hear it → Crew listens to the note and fixes the caption by hand
        post.status = ApprovalStatus.changes_requested
        post.client_feedback = "(voice note — see recording)"
        post.generation_meta = {**(post.generation_meta or {}), "needs_crew": True, "transcription": meta}
    else:
        post = await rewrite_post_from_feedback(db, settings, post, transcript)
        post.generation_meta = {**(post.generation_meta or {}), "transcription": meta}
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.put("/queue/{post_id}/caption", response_model=ContentQueueOut)
async def crew_update_caption(
    post_id: uuid.UUID,
    body: CrewCaptionEditBody,
    db: DbSession,
    crew: CrewUser,
) -> ContentQueueOut:
    """Crew hand-edit / reschedule; flagged or expired posts go back to the Captain."""
    post = await _load_queue_post(db, post_id, crew)
    if post.status in (ApprovalStatus.approved, ApprovalStatus.published):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit caption for status {post.status.value}",
        )
    if body.scheduled_publish_at is not None and body.scheduled_publish_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="scheduled_publish_at must be in the future")
    if post.status == ApprovalStatus.expired and body.scheduled_publish_at is None:
        raise HTTPException(
            status_code=400, detail="Expired posts need a new scheduled_publish_at"
        )
    crew_edit_caption(post, body.caption_text, scheduled_publish_at=body.scheduled_publish_at)
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.post("/queue/{post_id}/publish-retry", response_model=ContentQueueOut)
async def retry_publish(
    post_id: uuid.UUID,
    db: DbSession,
    crew: CrewUser,
) -> ContentQueueOut:
    """Crew: clear a publish failure so the worker tries again on its next run."""
    post = await _load_queue_post(db, post_id, crew)
    if post.status != ApprovalStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved posts can be retried")
    meta = dict(post.generation_meta or {})
    for key in ("publish_failed", "publish_attempts", "publish_error"):
        meta.pop(key, None)
    post.generation_meta = meta
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.post("/queue/{post_id}/mark-published", response_model=ContentQueueOut)
async def mark_published(
    post_id: uuid.UUID,
    db: DbSession,
    crew: CrewUser,
) -> ContentQueueOut:
    """Crew: record a post sent by hand (email / SMS channels have no auto-publisher yet)."""
    post = await _load_queue_post(db, post_id, crew)
    if post.status != ApprovalStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved posts can be marked published")
    meta = dict(post.generation_meta or {})
    meta["published_at"] = datetime.now(UTC).isoformat()
    meta["published_manually_by"] = str(crew.user_id)
    meta.pop("needs_manual_publish", None)
    post.generation_meta = meta
    post.status = ApprovalStatus.published
    post.published_external_id = "manual"
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.post("/queue/{post_id}/swap-asset", response_model=ContentQueueOut)
async def swap_asset(
    post_id: uuid.UUID,
    body: SwapAssetBody,
    db: DbSession,
    captain: CaptainUser,
) -> ContentQueueOut:
    post = await _load_queue_post(db, post_id, captain)
    if post.status not in (ApprovalStatus.pending_client, ApprovalStatus.changes_requested):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot swap asset for status {post.status.value}",
        )
    asset = (
        await db.execute(
            select(MediaAsset).where(
                MediaAsset.asset_id == body.asset_id,
                MediaAsset.client_id == post.client_id,
            )
        )
    ).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found for this client")
    post.asset_id = asset.asset_id
    asset.is_used = True
    await db.commit()
    await db.refresh(post)
    return _post_out(post)


@router.post("/clients/{client_id}/queue/approve-all", response_model=list[ContentQueueOut])
async def approve_all(
    client_id: TenantClientId,
    db: DbSession,
    _captain: CaptainUser,
) -> list[ContentQueueOut]:
    result = await db.execute(
        select(ContentQueue).where(
            ContentQueue.client_id == client_id,
            ContentQueue.status == ApprovalStatus.pending_client,
        )
    )
    posts = list(result.scalars().all())
    if not posts:
        raise HTTPException(status_code=404, detail="No pending_client posts to approve")
    for post in posts:
        post.status = ApprovalStatus.approved
    await db.commit()
    for post in posts:
        await db.refresh(post)
    return [_post_out(p) for p in posts]
