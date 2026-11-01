-- AI Finance Controller
-- F9.2 Bug #5: business-scoped audit records
--
-- Audit records authored for a business-carried action are tagged with the
-- business so that the business-scoped audit listing can isolate members
-- from personal data. Historical rows keep NULL (personal scope) unchanged.

ALTER TABLE audit_records
    ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES businesses(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_audit_records_business_id
    ON audit_records (business_id);

CREATE INDEX IF NOT EXISTS idx_audit_records_user_business_created
    ON audit_records (user_id, business_id, created_at DESC);