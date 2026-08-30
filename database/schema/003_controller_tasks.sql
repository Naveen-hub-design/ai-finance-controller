-- AI Finance Controller
-- Milestone 7.5: Async controller task ownership

-- Binds a dispatched Celery "run_ai_controller" task to the authenticated
-- user who submitted it, so that a task_id alone cannot authorize reading a
-- task result. Authorization-only; stores no financial data, no AI contents,
-- and no secrets.

CREATE TABLE IF NOT EXISTS controller_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_controller_tasks_task_id
    ON controller_tasks (task_id);

CREATE INDEX IF NOT EXISTS idx_controller_tasks_user_id
    ON controller_tasks (user_id);
