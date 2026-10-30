-- A-hoy Phase 1 Milestone A: core schema with Captain/Crew/Ship roles + MVP gaps
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_role AS ENUM ('captain', 'crew', 'deckhand', 'admin');
CREATE TYPE subscription_tier AS ENUM ('harbor', 'cruiser', 'flagship');

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(30),
    role user_role NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE clients (
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(200) NOT NULL,
    industry_vertical VARCHAR(100) NOT NULL,
    tier subscription_tier NOT NULL DEFAULT 'harbor',
    owner_user_id UUID REFERENCES users(user_id) ON DELETE RESTRICT,
    assigned_crew_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    twilio_tracking_number VARCHAR(30),
    gbp_location_id VARCHAR(120),
    pos_provider VARCHAR(50),
    average_ticket_value NUMERIC(10, 2) DEFAULT 150.00,
    conversion_rate_estimate NUMERIC(4, 2) DEFAULT 0.25,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE brand_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID UNIQUE REFERENCES clients(client_id) ON DELETE CASCADE,
    brand_voice_guidelines TEXT NOT NULL,
    target_zip_codes TEXT[],
    compliance_rules TEXT,
    services_offered JSONB,
    context_embedding vector(1536),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TYPE shoot_status AS ENUM ('scheduled', 'shot_list_ready', 'completed', 'processing', 'cancelled');

CREATE TABLE shoots (
    shoot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    creator_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    scheduled_start TIMESTAMPTZ NOT NULL,
    scheduled_end TIMESTAMPTZ NOT NULL,
    ai_shot_list JSONB,
    status shoot_status DEFAULT 'scheduled',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TYPE media_type AS ENUM ('raw_video', 'sliced_reel', 'raw_photo', 'enhanced_photo');

CREATE TABLE media_assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    shoot_id UUID REFERENCES shoots(shoot_id) ON DELETE SET NULL,
    storage_url TEXT NOT NULL,
    thumbnail_url TEXT,
    asset_type media_type NOT NULL,
    ai_tags TEXT[],
    transcript TEXT,
    duration_seconds INTEGER,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TYPE approval_status AS ENUM ('draft_internal', 'pending_client', 'approved', 'changes_requested', 'published');
CREATE TYPE platform_channel AS ENUM ('instagram_reel', 'instagram_post', 'facebook', 'tiktok', 'gbp_update', 'email_blast', 'sms_promo');

CREATE TABLE content_queue (
    post_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    asset_id UUID REFERENCES media_assets(asset_id) ON DELETE SET NULL,
    channel platform_channel NOT NULL,
    caption_text TEXT NOT NULL,
    scheduled_publish_at TIMESTAMPTZ NOT NULL,
    status approval_status DEFAULT 'draft_internal',
    client_feedback TEXT,
    voice_feedback_url TEXT,
    generation_meta JSONB,
    published_external_id VARCHAR(150),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TYPE flare_status AS ENUM ('submitted', 'ai_drafting', 'awaiting_client_signoff', 'launched');

CREATE TABLE flare_requests (
    flare_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    raw_owner_prompt TEXT NOT NULL,
    generated_post_id UUID REFERENCES content_queue(post_id) ON DELETE SET NULL,
    status flare_status DEFAULT 'submitted',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE daily_roi_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    tracked_calls_count INTEGER DEFAULT 0,
    form_leads_count INTEGER DEFAULT 0,
    gbp_direction_requests INTEGER DEFAULT 0,
    new_reviews_count INTEGER DEFAULT 0,
    ad_spend_usd NUMERIC(10, 2) DEFAULT 0.00,
    pos_attributed_revenue_usd NUMERIC(10, 2) DEFAULT 0.00,
    UNIQUE(client_id, metric_date)
);

-- Auth (magic link / OTP — sign-in only)
CREATE TABLE auth_magic_links (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    redirect_path TEXT DEFAULT '/queue',
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_jti VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Push tokens for Ship nudges
CREATE TYPE push_platform AS ENUM ('ios', 'android', 'web');

CREATE TABLE device_push_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    platform push_platform NOT NULL,
    token TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, token)
);

-- Reviews (Reputation Radar)
CREATE TYPE review_provider AS ENUM ('google', 'yelp', 'facebook');
CREATE TYPE reply_status AS ENUM ('auto_sent', 'awaiting_captain', 'captain_approved', 'skipped');

CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    provider review_provider NOT NULL,
    external_id VARCHAR(200) NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body TEXT,
    reviewer_name VARCHAR(150),
    ai_reply TEXT,
    reply_status reply_status,
    generation_meta JSONB,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, provider, external_id)
);

-- Integration credentials
CREATE TABLE integration_credentials (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    encrypted_payload TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, provider)
);

-- Lead events feeding ROI
CREATE TYPE lead_event_type AS ENUM ('tracked_call', 'form_lead', 'gbp_direction');

CREATE TABLE lead_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    event_type lead_event_type NOT NULL,
    external_id VARCHAR(200),
    duration_seconds INTEGER,
    metadata JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_queue_client_status ON content_queue(client_id, status);
CREATE INDEX idx_media_assets_client_tags ON media_assets USING GIN(ai_tags);
CREATE INDEX idx_daily_roi_client_date ON daily_roi_metrics(client_id, metric_date DESC);
CREATE INDEX idx_auth_magic_links_hash ON auth_magic_links(token_hash);
CREATE INDEX idx_device_push_tokens_user ON device_push_tokens(user_id) WHERE enabled = TRUE;
CREATE INDEX idx_reviews_client_status ON reviews(client_id, reply_status);
CREATE INDEX idx_lead_events_client_occurred ON lead_events(client_id, occurred_at DESC);
CREATE INDEX idx_sessions_jti ON sessions(token_jti);
