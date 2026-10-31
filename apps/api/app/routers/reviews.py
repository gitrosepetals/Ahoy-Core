import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.deps import AppSettings, CaptainUser, DbSession, TenantClientId, require_roles
from app.models import Review, UserRole
from app.schemas import AuthUser, ReviewOut
from app.services.reviews import (
    approve_review_reply,
    ensure_ai_reply,
    list_client_reviews,
    needs_captain,
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


@router.post("/reviews/{review_id}/approve-reply", response_model=ReviewOut)
async def approve_reply(
    review_id: uuid.UUID,
    db: DbSession,
    settings: AppSettings,
    captain: CaptainUser,
) -> ReviewOut:
    result = await db.execute(select(Review).where(Review.review_id == review_id))
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if captain.role != UserRole.admin and review.client_id not in captain.client_ids:
        raise HTTPException(status_code=403, detail="Client out of scope")
    review = await approve_review_reply(db, settings, review)
    await db.commit()
    await db.refresh(review)
    return _out(review)
