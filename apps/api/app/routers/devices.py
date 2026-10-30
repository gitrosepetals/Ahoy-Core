from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import DevicePushToken
from app.schemas import PushTokenRequest, PushTokenResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/push-token", response_model=PushTokenResponse)
async def register_push_token(
    body: PushTokenRequest,
    user: CurrentUser,
    db: DbSession,
) -> PushTokenResponse:
    result = await db.execute(
        select(DevicePushToken).where(
            DevicePushToken.user_id == user.user_id,
            DevicePushToken.token == body.token,
        )
    )
    existing = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if existing:
        existing.platform = body.platform
        existing.enabled = True
        existing.last_seen_at = now
        await db.commit()
        await db.refresh(existing)
        return PushTokenResponse(token_id=existing.token_id, platform=existing.platform)

    row = DevicePushToken(
        user_id=user.user_id,
        platform=body.platform,
        token=body.token,
        enabled=True,
        last_seen_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return PushTokenResponse(token_id=row.token_id, platform=row.platform)


@router.delete("/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_token(
    user: CurrentUser,
    db: DbSession,
    token: str,
) -> None:
    result = await db.execute(
        select(DevicePushToken).where(
            DevicePushToken.user_id == user.user_id,
            DevicePushToken.token == token,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        raise HTTPException(status_code=404, detail="Push token not found")
    existing.enabled = False
    existing.last_seen_at = datetime.now(UTC)
    await db.commit()
