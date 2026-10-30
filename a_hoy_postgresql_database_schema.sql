-- ============================================================================
-- A-HOY MARKETING SOLUTIONS - POSTGRESQL DATABASE SCHEMA (WITH PGVECTOR)
-- ============================================================================

-- Enable pgvector for Brand Brain RAG embeddings and pgcrypto for UUIDs
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. USERS & ROLES (Clients, Account Captains, Field Creators)
CREATE TYPE user_role AS ENUM ('client_owner', 'account_captain', 'field_creator', 'admin');
CREATE TYPE subscription_tier AS ENUM ('harbor', 'cruiser', 'flagship');

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(30),
    role user_role NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. CLIENTS (SMB Tenants)
CREATE TABLE clients (
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(200) NOT NULL,
    industry_vertical VARCHAR(100) NOT NULL, -- e.g., 'Optometry', 'HVAC', 'Cafe'
    tier subscription_tier NOT NULL DEFAULT 'harbor',
    owner_user_id UUID REFERENCES users(user_id) ON DELETE RESTRICT,
    assigned_captain_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    twilio_tracking_number VARCHAR(30),
    gbp_location_id VARCHAR(120),            -- Google Business Profile ID
    pos_provider VARCHAR(50),                -- e.g., 'square', 'clover', 'patient_pms'
    average_ticket_value NUMERIC(10, 2) DEFAULT 150.00, -- Used for ROI estimation
    conversion_rate_estimate NUMERIC(4, 2) DEFAULT 0.25, -- Default 25% lead-to-sale
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. BRAND BRAIN (Structured Context + Vector Embeddings for AI Generation)
CREATE TABLE brand_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID UNIQUE REFERENCES clients(client_id) ON DELETE CASCADE,
    brand_voice_guidelines TEXT NOT NULL,    -- e.g., 'Warm, clinical yet accessible, neighborhood-focused'
    target_zip_codes TEXT[],                 -- e.g., ARRAY['75080', '75040', '75081']
    compliance_rules TEXT,                   -- e.g., 'No guaranteed medical outcomes; include TX optometry disclaimer'
    services_offered JSONB,                  -- Structured list of services & prices
    context_embedding vector(1536),          -- OpenAI text-embedding-3-small vector
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ON-SITE SHOOTS (The "Docking" Schedule)
CREATE TYPE shoot_status AS ENUM ('scheduled', 'shot_list_ready', 'completed', 'processing', 'cancelled');

CREATE TABLE shoots (
    shoot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    creator_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    scheduled_start TIMESTAMPTZ NOT NULL,
    scheduled_end TIMESTAMPTZ NOT NULL,
    ai_shot_list JSONB,                      -- Generated checklist of scenes/prompts for the Field Creator
    status shoot_status DEFAULT 'scheduled',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. MEDIA ASSET VAULT (Raw & AI-Sliced Content)
CREATE TYPE media_type AS ENUM ('raw_video', 'sliced_reel', 'raw_photo', 'enhanced_photo');

CREATE TABLE media_assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    shoot_id UUID REFERENCES shoots(shoot_id) ON DELETE SET NULL,
    storage_url TEXT NOT NULL,               -- Azure Blob / AWS S3 URL
    thumbnail_url TEXT,
    asset_type media_type NOT NULL,
    ai_tags TEXT[],                          -- e.g., ARRAY['staff_intro', 'exam_room', 'eyewear_display']
    transcript TEXT,                         -- Whisper API transcript for video clips
    duration_seconds INTEGER,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. CONTENT APPROVAL QUEUE (The Tinder-Style Client Feed)
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
    client_feedback TEXT,                    -- Populated if owner clicks "Request Edit"
    published_external_id VARCHAR(150),      -- API response ID once live
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. "FLARE GUN" INSTANT PROMO TRIGGERS
CREATE TYPE flare_status AS ENUM ('submitted', 'ai_drafting', 'awaiting_client_signoff', 'launched');

CREATE TABLE flare_requests (
    flare_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    raw_owner_prompt TEXT NOT NULL,          -- e.g., '4 open slots Friday afternoon, 20% off frames'
    generated_post_id UUID REFERENCES content_queue(post_id) ON DELETE SET NULL,
    status flare_status DEFAULT 'submitted',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. DAILY ROI & ATTRIBUTION METRICS ("The Treasure Map")
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

-- 9. INDEXES FOR PERFORMANCE
CREATE INDEX idx_content_queue_client_status ON content_queue(client_id, status);
CREATE INDEX idx_media_assets_client_tags ON media_assets USING GIN(ai_tags);
CREATE INDEX idx_daily_roi_client_date ON daily_roi_metrics(client_id, metric_date DESC);