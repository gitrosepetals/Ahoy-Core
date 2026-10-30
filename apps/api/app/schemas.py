import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import PushPlatform, UserRole


class MagicLinkRequest(BaseModel):
    phone_number: str | None = None
    email: EmailStr | None = None
    redirect_path: str = "/queue"


class MagicLinkResponse(BaseModel):
    message: str
    # Returned only when AUTH_DEV_MODE=true
    dev_magic_link: str | None = None
    expires_in_minutes: int


class AuthUser(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    phone_number: str | None
    role: UserRole
    client_ids: list[uuid.UUID] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: AuthUser
    redirect_path: str = "/queue"


class PushTokenRequest(BaseModel):
    token: str = Field(min_length=8)
    platform: PushPlatform


class PushTokenResponse(BaseModel):
    ok: bool = True
    token_id: uuid.UUID
    platform: PushPlatform


class ClientSummary(BaseModel):
    client_id: uuid.UUID
    business_name: str
    industry_vertical: str
    tier: str


class MeResponse(BaseModel):
    user: AuthUser
    clients: list[ClientSummary]
