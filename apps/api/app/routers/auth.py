from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import AppSettings, CurrentUser, DbSession
from app.models import Client
from app.schemas import (
    ClientSummary,
    MagicLinkRequest,
    MagicLinkResponse,
    MeResponse,
    TokenResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    body: MagicLinkRequest,
    db: DbSession,
    settings: AppSettings,
) -> MagicLinkResponse:
    if not body.phone_number and not body.email:
        raise HTTPException(status_code=400, detail="Provide phone_number or email")

    user = await auth_service.find_user_for_magic_link(
        db, phone_number=body.phone_number, email=body.email
    )
    if user is None:
        # Do not leak whether the account exists
        return MagicLinkResponse(
            message="If an account exists, a sign-in link is on its way.",
            expires_in_minutes=settings.magic_link_ttl_minutes,
        )

    verify_url, _ = await auth_service.issue_magic_link(
        db,
        user=user,
        redirect_path=body.redirect_path,
        settings=settings,
    )
    return MagicLinkResponse(
        message="If an account exists, a sign-in link is on its way.",
        dev_magic_link=verify_url if settings.auth_dev_mode else None,
        expires_in_minutes=settings.magic_link_ttl_minutes,
    )


@router.get("/verify", response_model=TokenResponse)
async def verify_magic_link(
    db: DbSession,
    settings: AppSettings,
    token: str = Query(..., min_length=8),
) -> TokenResponse:
    try:
        access_token, expires_at, user, redirect_path = await auth_service.consume_magic_link(
            db, raw_token=token, settings=settings
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=user,
        redirect_path=redirect_path,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser, db: DbSession) -> MeResponse:
    clients: list[ClientSummary] = []
    if user.client_ids:
        result = await db.execute(select(Client).where(Client.client_id.in_(user.client_ids)))
        for client in result.scalars().all():
            clients.append(
                ClientSummary(
                    client_id=client.client_id,
                    business_name=client.business_name,
                    industry_vertical=client.industry_vertical,
                    tier=client.tier.value,
                )
            )
    return MeResponse(user=user, clients=clients)
