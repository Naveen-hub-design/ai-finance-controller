-- AI Finance Controller
-- Milestone: Multi-source financial reconciliation hardening
--
-- Adds durable per-line exception classification and human-review metadata to
-- statement_lines:
--
--   category       VARCHAR(40)  Deterministic exception category for an
--                               unmatched line (e.g. 'MISSING_LEDGER_RECORD',
--                               'AMOUNT_MISMATCH', 'DATE_MISMATCH',
--                               'DUPLICATE_RECORD', 'INVALID_RECORD'). NULL
--                               for pending/matched lines.
--   review_status  VARCHAR(20)  Human review loop status for the line:
--                               'UNRESOLVED' -> 'REVIEWED' -> 'RESOLVED'.
--                               Defaults to 'UNRESOLVED'.
--
-- Both additions are idempotent (ADD COLUMN IF NOT EXISTS): repeated
-- execution is a no-op, existing data is preserved, and no destructive or
-- data-mutating operation is performed.
ALTER TABLE statement_lines
    ADD COLUMN IF NOT EXISTS category VARCHAR(40);

ALTER TABLE statement_lines
    ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) NOT NULL DEFAULT 'UNRESOLVED';
