import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models import (
    ApprovalStatus,
    MediaType,
    PlatformChannel,
    PushPlatform,
    SubscriptionTier,
    UserRole,
)


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


class NotificationOut(BaseModel):
    notification_id: uuid.UUID
    kind: str
    channel: str
    status: str
    deep_link: str | None = None
    body: str | None = None
    error: str | None = None
    created_at: datetime | None = None


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
    pricing_notes: str | None = None
    seasonal_offers: Any | None = None
    local_seo_keywords: list[str] | None = None
    has_embedding: bool = False
    updated_at: datetime | None = None


class BrandProfileUpdate(BaseModel):
    brand_voice_guidelines: str = Field(min_length=1)
    target_zip_codes: list[str] | None = None
    compliance_rules: str | None = None
    services_offered: Any | None = None
    pricing_notes: str | None = None
    seasonal_offers: Any | None = None
    local_seo_keywords: list[str] | None = None


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
    # AG-03 single batch: one formatted variation per channel for every slot
    fan_out: bool = False


class ContentQueueOut(BaseModel):
    post_id: uuid.UUID
    client_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    channel: PlatformChannel
    caption_text: str
    scheduled_publish_at: datetime
    status: ApprovalStatus
    client_feedback: str | None = None
    voice_feedback_url: str | None = None
    generation_meta: dict | None = None
    created_at: datetime | None = None


class QueueReleaseRequest(BaseModel):
    post_ids: list[uuid.UUID] | None = None


class RequestEditBody(BaseModel):
    feedback: str = Field(min_length=1, max_length=4000)


class CrewCaptionEditBody(BaseModel):
    caption_text: str = Field(min_length=1, max_length=5000)
    # Required to revive an expired post; optional otherwise
    scheduled_publish_at: datetime | None = None


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
    impressions: int = 0
    clicks: int = 0


class RoiDetail(BaseModel):
    impressions: int
    clicks: int
    ctr: float | None = None
    gbp_direction_requests: int
    cost_per_lead_usd: float | None = None


class RoiSummary(BaseModel):
    client_id: uuid.UUID
    days: int
    period: str
    period_start: str
    period_end: str
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
    qualified_call_min_seconds: int
    detail: RoiDetail


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
    reply_due_at: datetime | None = None
    reply_posted_at: datetime | None = None
    reply_error: str | None = None
    can_reply: bool = True


class ApproveReplyBody(BaseModel):
    reply_text: str | None = Field(default=None, max_length=4000)


class MarketingLeadRequest(BaseModel):
    email: EmailStr
    business_name: str | None = Field(default=None, max_length=200)
    source: str = Field(default="welcome", max_length=80)


class MarketingLeadResponse(BaseModel):
    ok: bool = True
    email: str


class ClientSettingsOut(BaseModel):
    client_id: uuid.UUID
    business_name: str
    twilio_tracking_number: str | None = None
    gbp_location_id: str | None = None
    pos_provider: str | None = None
    average_ticket_value: float
    conversion_rate_estimate: float
    billing_anchor_day: int
    forward_to_number: str | None = None
    record_calls: bool = True
    timezone: str
    auto_reply_delay_hours: int
    facebook_page_id: str | None = None
    yelp_business_id: str | None = None
    lead_form_key: str | None = None
    lead_form_url: str | None = None
    twilio_voice_webhook_url: str


class ClientSettingsUpdate(BaseModel):
    twilio_tracking_number: str | None = Field(default=None, max_length=30)
    gbp_location_id: str | None = Field(default=None, max_length=120)
    pos_provider: str | None = Field(default=None, max_length=50)
    average_ticket_value: float | None = Field(default=None, ge=0, le=99999999)
    conversion_rate_estimate: float | None = Field(default=None, ge=0, le=1)
    billing_anchor_day: int | None = Field(default=None, ge=1, le=28)
    forward_to_number: str | None = Field(default=None, max_length=30)
    record_calls: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)
    auto_reply_delay_hours: int | None = Field(default=None, ge=0, le=72)
    facebook_page_id: str | None = Field(default=None, max_length=80)
    yelp_business_id: str | None = Field(default=None, max_length=120)


class IntegrationOut(BaseModel):
    provider: str
    connected: bool
    updated_at: datetime | None = None


class AyrshareCredentialBody(BaseModel):
    profile_key: str = Field(min_length=8, max_length=200)


class LeadEventOut(BaseModel):
    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    duration_seconds: int | None = None
    qualified: bool
    caller: str | None = None
    call_status: str | None = None
    has_recording: bool = False
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    message: str | None = None


class ManualMetricsBody(BaseModel):
    """Crew concierge entry for sources not integrated yet (ad spend, impressions, POS $)."""

    metric_date: date
    ad_spend_usd: float | None = Field(default=None, ge=0)
    impressions: int | None = Field(default=None, ge=0)
    clicks: int | None = Field(default=None, ge=0)
    gbp_direction_requests: int | None = Field(default=None, ge=0)
    pos_attributed_revenue_usd: float | None = Field(default=None, ge=0)


class FacebookCredentialBody(BaseModel):
    page_id: str = Field(min_length=3, max_length=80)
    page_access_token: str = Field(min_length=20, max_length=1000)


class GoogleLocationOut(BaseModel):
    name: str
    title: str | None = None


class BillingOut(BaseModel):
    tier: str
    subscription_status: str
    current_period_end: datetime | None = None
    has_customer: bool
    billing_enabled: bool


class CheckoutBody(BaseModel):
    tier: SubscriptionTier


class UrlOut(BaseModel):
    url: str


class AdSpendBody(BaseModel):
    amount_usd: float = Field(gt=0, le=100000)
    description: str = Field(default="Ad spend (pass-through)", min_length=1, max_length=200)


class AuditEventOut(BaseModel):
    audit_id: uuid.UUID
    actor_role: str
    actor_user_id: uuid.UUID | None = None
    entity_type: str
    entity_id: str | None = None
    action: str
    from_status: str | None = None
    to_status: str | None = None
    created_at: datetime | None = None
