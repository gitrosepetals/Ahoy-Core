import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models import ApprovalStatus, MediaType, PlatformChannel, PushPlatform, UserRole


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


class BrandProfileOut(BaseModel):
    profile_id: uuid.UUID
    client_id: uuid.UUID
    brand_voice_guidelines: str
    target_zip_codes: list[str] | None = None
    compliance_rules: str | None = None
    services_offered: Any | None = None
    has_embedding: bool = False
    updated_at: datetime | None = None


class BrandProfileUpdate(BaseModel):
    brand_voice_guidelines: str = Field(min_length=1)
    target_zip_codes: list[str] | None = None
    compliance_rules: str | None = None
    services_offered: Any | None = None


class MediaAssetOut(BaseModel):
    asset_id: uuid.UUID
    client_id: uuid.UUID
    storage_url: str
    thumbnail_url: str | None = None
    asset_type: MediaType
    ai_tags: list[str] | None = None
    is_used: bool = False
    created_at: datetime | None = None


class MediaRegisterRequest(BaseModel):
    storage_url: str = Field(min_length=1)
    thumbnail_url: str | None = None
    asset_type: MediaType = MediaType.raw_photo
    ai_tags: list[str] | None = None


class CampaignGenerateRequest(BaseModel):
    asset_ids: list[uuid.UUID] = Field(default_factory=list)
    channels: list[PlatformChannel] = Field(
        default_factory=lambda: [PlatformChannel.instagram_post, PlatformChannel.facebook]
    )
    days: int = Field(default=7, ge=1, le=60)
    count: int = Field(default=4, ge=1, le=20)


class ContentQueueOut(BaseModel):
    post_id: uuid.UUID
    client_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    channel: PlatformChannel
    caption_text: str
    scheduled_publish_at: datetime
    status: ApprovalStatus
    client_feedback: str | None = None
    generation_meta: dict | None = None
    created_at: datetime | None = None


class QueueReleaseRequest(BaseModel):
    post_ids: list[uuid.UUID] | None = None


class RequestEditBody(BaseModel):
    feedback: str = Field(min_length=1, max_length=4000)


class SwapAssetBody(BaseModel):
    asset_id: uuid.UUID


class RoiDayRow(BaseModel):
    metric_date: str
    tracked_calls_count: int
    form_leads_count: int
    gbp_direction_requests: int
    new_reviews_count: int
    ad_spend_usd: float
    pos_attributed_revenue_usd: float
    estimated_revenue_usd: float


class RoiSummary(BaseModel):
    client_id: uuid.UUID
    days: int
    total_calls: int
    total_form_leads: int
    total_leads: int
    total_reviews: int
    total_ad_spend_usd: float
    total_pos_revenue_usd: float
    estimated_revenue_usd: float
    using_pos: bool
    average_ticket_value: float
    conversion_rate_estimate: float


class ReviewOut(BaseModel):
    review_id: uuid.UUID
    client_id: uuid.UUID
    provider: str
    external_id: str
    rating: int
    body: str | None = None
    reviewer_name: str | None = None
    ai_reply: str | None = None
    reply_status: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    needs_captain: bool = False
