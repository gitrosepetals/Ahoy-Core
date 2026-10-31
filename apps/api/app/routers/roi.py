from fastapi import APIRouter, Depends, Query

from app.deps import DbSession, TenantClientId, require_roles
from app.models import UserRole
from app.schemas import AuthUser, RoiDayRow, RoiSummary
from app.services.roi import summarize_roi

router = APIRouter(prefix="/clients", tags=["roi"])


@router.get("/{client_id}/roi", response_model=RoiSummary)
async def get_roi(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = Depends(require_roles(UserRole.captain, UserRole.crew)),
    days: int = Query(default=30, ge=1, le=90),
) -> RoiSummary:
    summary, _ = await summarize_roi(db, client_id, days=days)
    return RoiSummary(**summary)


@router.get("/{client_id}/roi/breakdown", response_model=list[RoiDayRow])
async def get_roi_breakdown(
    client_id: TenantClientId,
    db: DbSession,
    _user: AuthUser = Depends(require_roles(UserRole.captain, UserRole.crew)),
    days: int = Query(default=30, ge=1, le=90),
) -> list[RoiDayRow]:
    _, breakdown = await summarize_roi(db, client_id, days=days)
    return [RoiDayRow(**row) for row in breakdown]
