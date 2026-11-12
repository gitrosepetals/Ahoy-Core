-- 0.8.0 — Real notifications (CL-02 / Story 1.1 / CL-05) + approval-queue expiry

-- A post the Captain never approved before its publish time can't go out; it becomes
-- 'expired' and returns to Crew to reschedule.
ALTER TYPE approval_status ADD VALUE IF NOT EXISTS 'expired';

ALTER TABLE content_queue
    ADD COLUMN IF NOT EXISTS released_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ;

-- Low-star alert dedupe (BUG-003): alert once per review.
ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS alerted_at TIMESTAMPTZ;

-- Every owner notification attempt (push / SMS / dev log): delivery audit + PRD §7 KPIs.
CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    kind VARCHAR(50) NOT NULL,          -- queue_ready | queue_expiring | low_star_review | ...
    channel VARCHAR(20) NOT NULL,       -- push | sms | log
    status VARCHAR(20) NOT NULL,        -- sent | failed | logged
    deep_link TEXT,
    body TEXT,
    payload JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_client_created ON notifications (client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_queue_pending_schedule
    ON content_queue (scheduled_publish_at) WHERE status IN ('pending_client', 'changes_requested');
