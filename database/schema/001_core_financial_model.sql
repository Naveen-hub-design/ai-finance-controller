-- AI Finance Controller
-- Milestone 2: Core financial data model

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    current_balance NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT accounts_account_type_check
        CHECK (account_type IN (
            'bank',
            'cash',
            'credit_card',
            'investment',
            'loan',
            'other'
        )),

    CONSTRAINT accounts_currency_check
        CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    category_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT categories_type_check
        CHECK (category_type IN ('income', 'expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    amount NUMERIC(19,4) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    description TEXT,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT transactions_amount_check
        CHECK (amount >= 0),

    CONSTRAINT transactions_type_check
        CHECK (transaction_type IN ('income', 'expense', 'transfer'))
);

CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    amount NUMERIC(19,4) NOT NULL,
    period VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT budgets_amount_check
        CHECK (amount >= 0),

    CONSTRAINT budgets_period_check
        CHECK (period IN ('weekly', 'monthly', 'yearly')),

    CONSTRAINT budgets_dates_check
        CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS financial_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    target_amount NUMERIC(19,4) NOT NULL,
    current_amount NUMERIC(19,4) NOT NULL DEFAULT 0,
    target_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT goals_target_check
        CHECK (target_amount > 0),

    CONSTRAINT goals_current_check
        CHECK (current_amount >= 0),

    CONSTRAINT goals_status_check
        CHECK (status IN ('active', 'completed', 'paused', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id
    ON accounts(user_id);

CREATE INDEX IF NOT EXISTS idx_categories_user_id
    ON categories(user_id);

CREATE INDEX IF NOT EXISTS idx_transactions_account_id
    ON transactions(account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON transactions(transaction_date);

CREATE INDEX IF NOT EXISTS idx_transactions_category_id
    ON transactions(category_id);

CREATE INDEX IF NOT EXISTS idx_budgets_user_id
    ON budgets(user_id);

CREATE INDEX IF NOT EXISTS idx_goals_user_id
    ON financial_goals(user_id);
