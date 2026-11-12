-- 0.15.0 — Audit log of status transitions + sensitive changes (Milestone D observability)

CREATE TABLE IF NOT EXISTS audit_events (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(client_id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    actor_role VARCHAR(20) NOT NULL,     -- captain | crew | admin | system | webhook
    entity_type VARCHAR(40) NOT NULL,    -- post | review | integration | billing
    entity_id VARCHAR(80),
    action VARCHAR(60) NOT NULL,         -- status_change | credential_saved | ...
    from_status VARCHAR(40),
    to_status VARCHAR(40),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_client_created ON audit_events (client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events (entity_type, entity_id);
