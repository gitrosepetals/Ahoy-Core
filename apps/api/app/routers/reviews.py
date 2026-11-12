import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select

from app.deps import AppSettings, CaptainUser, CrewUser, DbSession, TenantClientId, require_roles
from app.models import Client, Review, UserRole
from app.schemas import ApproveReplyBody, AuthUser, ReviewOut
from app.services.review_providers import provider_can_reply
from app.services.reviews import (
    approve_review_reply,
    ensure_ai_reply,
    list_client_reviews,
    needs_captain,
    skip_review_reply,
    sync_client_reviews,
)

router = APIRouter(tags=["reviews"])


def _out(review: Review) -> ReviewOut:
    return ReviewOut(
        review_id=review.review_id,
        client_id=review.client_id,
        provider=review.provider.value if hasattr(review.provider, "value") else str(review.provider),
        external_id=review.external_id,
        rating=review.rating,
        body=review.body,
        reviewer_name=review.reviewer_name,
        ai_reply=review.ai_reply,
        reply_status=(
            review.reply_status.value
            if review.reply_status is not None and hasattr(review.reply_status, "value")
            else review.reply_status
        ),
        reviewed_at=review.reviewed_at,
        created_at=review.created_at,
        needs_captain=needs_captain(review),
        reply_due_at=review.reply_due_at,
        reply_posted_at=review.reply_posted_at,
        reply_error=review.reply_error,
        can_reply=provider_can_reply(review.provider),
    )


@router.get("/clients/{client_id}/reviews", response_model=list[ReviewOut])
async def get_reviews(
    client_id: TenantClientId,
    db: DbSession,
    settings: AppSettings,
    _user: AuthUser = Depends(require_roles(UserRole.captain, UserRole.crew)),
) -> list[ReviewOut]:
    reviews = await list_client_reviews(db, client_id)
    # Ensure drafts exist for any missing ai_reply (dev seed may already have them)
    out: list[ReviewOut] = []
    for review in reviews:
        review = await ensure_ai_reply(db, settings, review)
        out.append(_out(review))
    await db.commit()
    return out


@router.post("/clients/{client_id}/reviews/sync")
async def sync_reviews_now(
    client_id: TenantClientId,
    db: DbSession,
    settings: AppSettings,
    _crew: CrewUser,
) -> dict:
    """Crew: pull from connected providers now instead of waiting for the 30-minute job."""
    client = (await db.execute(select(Client).where(Client.client_id == client_id))).scalar_one()
    stats = await sync_client_reviews(db, settings, client)
    await db.commit()
    return stats


async def _load_review(db: DbSession, review_id: uuid.UUID, user: AuthUser) -> Review:
    review = (await db.execute(select(Review).where(Review.review_id == review_id))).scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if user.role != UserRole.admin and review.client_id not in user.client_ids:
        raise HTTPException(status_code=403, detail="Client out of scope")
    return review


@router.post("/reviews/{review_id}/approve-reply", response_model=ReviewOut)
async def approve_reply(
    review_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    captain: CaptainUser,
    body: ApproveReplyBody | None = Body(default=None),
) -> ReviewOut:
    review = await _load_review(db, review_id, captain)
    review = await approve_review_reply(
        db, settings, review, reply_text=body.reply_text if body else None
    )
    await db.commit()
    await db.refresh(review)
    return _out(review)


@router.post("/reviews/{review_id}/skip-reply", response_model=ReviewOut)
async def skip_reply(
    review_id: uuid.UUID,
    db: DbSession,
    captain: CaptainUser,
) -> ReviewOut:
    """Captain: don't post anything for this review (e.g. a scheduled 5★ reply)."""
    review = await _load_review(db, review_id, captain)
    if review.reply_posted_at is not None:
        raise HTTPException(status_code=400, detail="Reply already posted")
    review = await skip_review_reply(db, review)
    await db.commit()
    await db.refresh(review)
    return _out(review)
