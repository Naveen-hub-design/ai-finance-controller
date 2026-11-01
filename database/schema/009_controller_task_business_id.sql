-- AI Finance Controller
-- F9.2 Bug #10: business-scoped async task ownership
--
-- Async tasks dispatched for a business-carried job carry the business so
-- that business members (identity-bound to the URL user_id) can poll the
-- task status while personal tasks stay owner-only. Historical rows keep
-- NULL (personal/owner-only) unchanged.

ALTER TABLE controller_tasks
    ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES businesses(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_controller_tasks_business_id
    ON controller_tasks (business_id);