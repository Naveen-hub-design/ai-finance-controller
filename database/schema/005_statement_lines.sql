-- AI Finance Controller
-- Milestone: Multi-source financial reconciliation
--
-- The reconciliation agent closes a finance-ops loop across a batch of
-- records by matching an external source (source B) against the internal
-- ledger ("transactions", source A). This adds the statement_lines table that
-- holds source B lines, plus idempotent ADD of the user_id/business_id
-- scoping columns and the reconcile-outcome columns.
--
-- All statements are idempotent and additive: repeated execution is a no-op,
-- existing data is never dropped or modified.

CREATE TABLE IF NOT EXISTS statement_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL DEFAULT 'bank_statement',
    external_reference VARCHAR(255),
    amount NUMERIC(19, 4) NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    matched_transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_statement_lines_user_id
    ON statement_lines (user_id);
CREATE INDEX IF NOT EXISTS idx_statement_lines_business_id
    ON statement_lines (business_id);
CREATE INDEX IF NOT EXISTS idx_statement_lines_source
    ON statement_lines (source);
