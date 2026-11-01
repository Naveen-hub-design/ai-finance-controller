-- AI Finance Controller
-- Milestone: Multi-source financial reconciliation
--
-- The reconciliation agent persists an immutable `kind = 'reconciliation'`
-- audit record on every completed run. The original audit CHECK constraint
-- (m4_audit, Milestone 4.4) only allowed ('risk', 'recommendation',
-- 'decision'), so insertions of reconciliation records failed on databases
-- that were initialized before this milestone.
--
-- PostgreSQL cannot alter a CHECK constraint in place, so we DROP and re-ADD
-- it. The statement is idempotent / additive: it only re-creates the
-- constraint when the existing one does not yet allow 'reconciliation'.
-- Fresh databases already carry the widened check via 002_m4_audit.sql, and
-- databases whose constraint already allows reconciliation are untouched.
-- No existing data is dropped or modified.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'audit_records_kind_check'
          AND NOT pg_get_constraintdef(oid) ILIKE '%reconciliation%'
    ) THEN
        ALTER TABLE audit_records DROP CONSTRAINT audit_records_kind_check;
        ALTER TABLE audit_records ADD CONSTRAINT audit_records_kind_check
            CHECK (kind IN ('risk', 'recommendation', 'decision', 'reconciliation'));
    END IF;
END $$;
