-- AI Finance Controller
-- Milestone F9.x.1: Role-based authentication + multi-user business architecture.
--
-- Two concerns addressed here:
--
-- 1. Idempotent ADD of the users.role column (VARCHAR(32) NOT NULL DEFAULT
--    'MERCHANT'). Every pre-existing user automatically becomes a MERCHANT.
--    The CHECK constraint is added idempotently so the allowed values are
--    enforced without requiring a table recreate.
--
-- 2. businesses + business_members tables so a MERCHANT can create a business
--    (becoming its OWNER) and add FINANCE_MANAGER members. PLATFORM_ADMIN is
--    deliberately NOT a valid member role: it is a platform-level role, not a
--    business membership role. Member access never bypasses membership checks.
--
-- All statements are idempotent and additive: repeated execution is a no-op,
-- existing data is never dropped or modified.

-- users.role
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'MERCHANT';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_role'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT chk_users_role
            CHECK (role IN ('PLATFORM_ADMIN', 'MERCHANT', 'FINANCE_MANAGER'));
    END IF;
END $$;

-- businesses
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- business_members
CREATE TABLE IF NOT EXISTS business_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'FINANCE_MANAGER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_business_member UNIQUE (business_id, user_id),
    CONSTRAINT chk_business_member_role
        CHECK (role IN ('OWNER', 'FINANCE_MANAGER'))
);

CREATE INDEX IF NOT EXISTS idx_business_members_business_id
    ON business_members (business_id);
CREATE INDEX IF NOT EXISTS idx_business_members_user_id
    ON business_members (user_id);

-- Optional business scope on accounts (NULL => personal). Added idempotently
-- so an existing pre-F9.x.1 volume gains the column without any data loss.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS business_id UUID
    REFERENCES businesses(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_accounts_business_id
    ON accounts (business_id);

-- Optional business scope on budgets. Added idempotently.
ALTER TABLE budgets ADD COLUMN IF NOT EXISTS business_id UUID
    REFERENCES businesses(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_budgets_business_id
    ON budgets (business_id);

-- Optional business scope on financial goals. Added idempotently.
ALTER TABLE financial_goals ADD COLUMN IF NOT EXISTS business_id UUID
    REFERENCES businesses(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_financial_goals_business_id
    ON financial_goals (business_id);
