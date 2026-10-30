import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Client, UserRole
from app.schemas import AuthUser
from app.services.auth import load_user_from_token

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await load_user_from_token(db, credentials.credentials, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def _checker(user: CurrentUser) -> AuthUser:
        if user.role not in roles and user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in roles]}",
            )
        return user

    return _checker


CaptainUser = Annotated[AuthUser, Depends(require_roles(UserRole.captain))]
CrewUser = Annotated[AuthUser, Depends(require_roles(UserRole.crew))]


async def get_authorized_client_id(
    client_id: Annotated[uuid.UUID, Path()],
    user: CurrentUser,
    db: DbSession,
    x_client_id: Annotated[str | None, Header(alias="X-Client-Id")] = None,
) -> uuid.UUID:
    """Enforce multi-tenant access: user may only touch clients they belong to."""
    if user.role != UserRole.admin and client_id not in user.client_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client out of scope")

    # Optional header must match path when provided (defense in depth for Ship/Crew clients)
    if x_client_id:
        try:
            header_id = uuid.UUID(x_client_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid X-Client-Id") from exc
        if header_id != client_id:
            raise HTTPException(status_code=400, detail="X-Client-Id does not match path")

    result = await db.execute(select(Client.client_id).where(Client.client_id == client_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client_id


TenantClientId = Annotated[uuid.UUID, Depends(get_authorized_client_id)]
