-- 0.13.0 — Stripe Billing: subscription tier sync + ad-spend pass-through (PRD §4)

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(64),
    -- Stripe subscription status (active, trialing, past_due, canceled, unpaid, incomplete…) or 'none'
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(32) NOT NULL DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_clients_stripe_customer ON clients (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- Stripe retries webhooks; remember processed event ids so each is applied once.
CREATE TABLE IF NOT EXISTS stripe_events (
    event_id VARCHAR(80) PRIMARY KEY,
    event_type VARCHAR(80) NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW()
);
