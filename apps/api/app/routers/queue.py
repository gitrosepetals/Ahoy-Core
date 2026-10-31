import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
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
    QueueReleaseRequest,
    RequestEditBody,
    SwapAssetBody,
)
from app.services.campaigns import rewrite_post_from_feedback
from app.services.notify import notify_captain_queue_ready

router = APIRouter(tags=["queue"])


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

    for post in posts:
        post.status = ApprovalStatus.pending_client

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
