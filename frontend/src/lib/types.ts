export interface User {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
}

export type AccountType =
  | "bank"
  | "cash"
  | "credit_card"
  | "investment"
  | "loan"
  | "other";

export interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: AccountType;
  currency: string;
  current_balance: string;
  created_at: string;
  updated_at: string;
}

export type TransactionType = "income" | "expense" | "transfer";

export interface Transaction {
  id: string;
  account_id: string;
  category_id: string | null;
  amount: string;
  transaction_type: TransactionType;
  description: string | null;
  transaction_date: string;
  created_at: string;
}

export type CategoryType = "income" | "expense";

export interface Category {
  id: string;
  user_id: string | null;
  name: string;
  category_type: CategoryType;
  created_at: string;
}

export type BudgetPeriod = "weekly" | "monthly" | "yearly";

export interface Budget {
  id: string;
  user_id: string;
  category_id: string | null;
  amount: string;
  period: BudgetPeriod;
  start_date: string;
  end_date: string;
  created_at: string;
}

export type GoalStatus = "active" | "completed" | "paused" | "cancelled";

export interface FinancialGoal {
  id: string;
  user_id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  target_date: string | null;
  status: GoalStatus;
  created_at: string;
  updated_at: string;
}

export interface FinancialSummary {
  total_income: string;
  total_expenses: string;
  net_cash_flow: string;
  transaction_count: number;
  income_transaction_count: number;
  expense_transaction_count: number;
  account_balance: string;
}

export type AuditKind = "risk" | "recommendation" | "decision";

export interface AuditRecord {
  id: string;
  user_id: string;
  kind: AuditKind;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AsyncTaskStatus {
  task_id: string;
  status: "PENDING" | "SUCCESS" | "FAILURE" | "RETRY" | "STARTED";
  result?: unknown;
  message?: string;
}
