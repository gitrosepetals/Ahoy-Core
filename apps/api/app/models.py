import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    captain = "captain"
    crew = "crew"
    deckhand = "deckhand"
    admin = "admin"


class SubscriptionTier(str, enum.Enum):
    harbor = "harbor"
    cruiser = "cruiser"
    flagship = "flagship"


class PushPlatform(str, enum.Enum):
    ios = "ios"
    android = "android"
    web = "web"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role", create_type=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Client(Base):
    __tablename__ = "clients"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry_vertical: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier", create_type=False),
        nullable=False,
        default=SubscriptionTier.harbor,
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    assigned_crew_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    twilio_tracking_number: Mapped[str | None] = mapped_column(String(30))
    gbp_location_id: Mapped[str | None] = mapped_column(String(120))
    pos_provider: Mapped[str | None] = mapped_column(String(50))
    average_ticket_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("150.00"))
    conversion_rate_estimate: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.25"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(foreign_keys=[owner_user_id])
    assigned_crew: Mapped[User | None] = relationship(foreign_keys=[assigned_crew_id])


class AuthMagicLink(Base):
    __tablename__ = "auth_magic_links"

    link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    redirect_path: Mapped[str | None] = mapped_column(Text, default="/queue")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DevicePushToken(Base):
    __tablename__ = "device_push_tokens"
    __table_args__ = (UniqueConstraint("user_id", "token", name="uq_device_push_user_token"),)

    token_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    platform: Mapped[PushPlatform] = mapped_column(
        Enum(PushPlatform, name="push_platform", create_type=False), nullable=False
    )
    token: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyRoiMetric(Base):
    __tablename__ = "daily_roi_metrics"
    __table_args__ = (UniqueConstraint("client_id", "metric_date", name="uq_daily_roi_client_date"),)

    metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id"), nullable=False)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    tracked_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    form_leads_count: Mapped[int] = mapped_column(Integer, default=0)
    gbp_direction_requests: Mapped[int] = mapped_column(Integer, default=0)
    new_reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    ad_spend_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    pos_attributed_revenue_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))


class ReviewProvider(str, enum.Enum):
    google = "google"
    yelp = "yelp"
    facebook = "facebook"


class ReplyStatus(str, enum.Enum):
    auto_sent = "auto_sent"
    awaiting_captain = "awaiting_captain"
    captain_approved = "captain_approved"
    skipped = "skipped"


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("client_id", "provider", "external_id", name="uq_reviews_external"),)

    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id"), nullable=False)
    provider: Mapped[ReviewProvider] = mapped_column(
        Enum(ReviewProvider, name="review_provider", create_type=False), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    reviewer_name: Mapped[str | None] = mapped_column(String(150))
    ai_reply: Mapped[str | None] = mapped_column(Text)
    reply_status: Mapped[ReplyStatus | None] = mapped_column(
        Enum(ReplyStatus, name="reply_status", create_type=False)
    )
    generation_meta: Mapped[dict | None] = mapped_column(JSONB)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MediaType(str, enum.Enum):
    raw_video = "raw_video"
    sliced_reel = "sliced_reel"
    raw_photo = "raw_photo"
    enhanced_photo = "enhanced_photo"


class ApprovalStatus(str, enum.Enum):
    draft_internal = "draft_internal"
    pending_client = "pending_client"
    approved = "approved"
    changes_requested = "changes_requested"
    published = "published"


class PlatformChannel(str, enum.Enum):
    instagram_reel = "instagram_reel"
    instagram_post = "instagram_post"
    facebook = "facebook"
    tiktok = "tiktok"
    gbp_update = "gbp_update"
    email_blast = "email_blast"
    sms_promo = "sms_promo"


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    brand_voice_guidelines: Mapped[str] = mapped_column(Text, nullable=False)
    target_zip_codes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    compliance_rules: Mapped[str | None] = mapped_column(Text)
    services_offered: Mapped[dict | list | None] = mapped_column(JSONB)
    context_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False
    )
    # Column exists in DB; Shoot ORM deferred past Milestone B
    shoot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    asset_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type", create_type=False), nullable=False
    )
    ai_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    transcript: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentQueue(Base):
    __tablename__ = "content_queue"

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.asset_id", ondelete="SET NULL")
    )
    channel: Mapped[PlatformChannel] = mapped_column(
        Enum(PlatformChannel, name="platform_channel", create_type=False), nullable=False
    )
    caption_text: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status", create_type=False),
        default=ApprovalStatus.draft_internal,
        nullable=False,
    )
    client_feedback: Mapped[str | None] = mapped_column(Text)
    voice_feedback_url: Mapped[str | None] = mapped_column(Text)
    generation_meta: Mapped[dict | None] = mapped_column(JSONB)
    published_external_id: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingLead(Base):
    __tablename__ = "marketing_leads"

    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    business_name: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="welcome")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
