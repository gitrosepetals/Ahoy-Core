-- 0.10.0 — Closed-loop ROI data (CL-01 / Story 2.1): call tracking + form leads → rollup

ALTER TABLE clients
    -- Business's real line; the Twilio tracking number forwards here
    ADD COLUMN IF NOT EXISTS forward_to_number VARCHAR(30),
    -- Record forwarded calls (plays a consent notice first — IL and other all-party-consent states)
    ADD COLUMN IF NOT EXISTS record_calls BOOLEAN NOT NULL DEFAULT TRUE,
    -- Public key for website lead forms (POST /webhooks/forms/{key})
    ADD COLUMN IF NOT EXISTS lead_form_key VARCHAR(64),
    -- Local day boundaries for daily rollups
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) NOT NULL DEFAULT 'America/Chicago';

CREATE UNIQUE INDEX IF NOT EXISTS uq_clients_lead_form_key ON clients (lead_form_key) WHERE lead_form_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_clients_tracking_number ON clients (twilio_tracking_number) WHERE twilio_tracking_number IS NOT NULL;

-- Idempotent webhooks: Twilio retries must not double-count a call
CREATE UNIQUE INDEX IF NOT EXISTS uq_lead_events_external
    ON lead_events (client_id, event_type, external_id) WHERE external_id IS NOT NULL;

-- "Detailed View" vanity metrics (hidden by default per CL-01)
ALTER TABLE daily_roi_metrics
    ADD COLUMN IF NOT EXISTS impressions INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS clicks INTEGER DEFAULT 0;

UPDATE clients
SET lead_form_key = 'oaklawn-demo-form-key',
    forward_to_number = '+15551234099'
WHERE client_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' AND lead_form_key IS NULL;
