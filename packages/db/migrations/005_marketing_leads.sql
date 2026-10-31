-- Public welcome-page email capture
CREATE TABLE marketing_leads (
    lead_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    business_name VARCHAR(200),
    source VARCHAR(80) NOT NULL DEFAULT 'welcome',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT marketing_leads_email_unique UNIQUE (email)
);

CREATE INDEX idx_marketing_leads_created_at ON marketing_leads (created_at DESC);
