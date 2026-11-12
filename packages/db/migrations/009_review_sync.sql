-- 0.11.0 — Reputation Radar (CL-05): provider sync, real reply posting, auto-reply delay

-- 4-5★ replies wait here until reply_due_at (optional 24h delay), then the worker posts them.
ALTER TYPE reply_status ADD VALUE IF NOT EXISTS 'scheduled';

ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS reply_due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reply_posted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reply_error TEXT,
    -- Provider-specific handle needed to reply (e.g. Facebook open_graph_story id)
    ADD COLUMN IF NOT EXISTS reply_target VARCHAR(200);

ALTER TABLE clients
    -- 0 = post 4-5★ replies right away; PRD default "optional 24-hour delay"
    ADD COLUMN IF NOT EXISTS auto_reply_delay_hours SMALLINT NOT NULL DEFAULT 24
        CHECK (auto_reply_delay_hours BETWEEN 0 AND 72),
    ADD COLUMN IF NOT EXISTS facebook_page_id VARCHAR(80),
    ADD COLUMN IF NOT EXISTS yelp_business_id VARCHAR(120);

CREATE INDEX IF NOT EXISTS idx_reviews_reply_due ON reviews (reply_due_at)
    WHERE reply_posted_at IS NULL;
