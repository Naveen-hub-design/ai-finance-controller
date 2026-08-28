-- AI Finance Controller
-- Milestone 4.4: Decision / audit trail

CREATE TABLE IF NOT EXISTS audit_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT audit_records_kind_check
        CHECK (kind IN ('risk', 'recommendation', 'decision'))
);

CREATE INDEX IF NOT EXISTS idx_audit_records_user_id
    ON audit_records (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_records_user_created
    ON audit_records (user_id, created_at DESC);
