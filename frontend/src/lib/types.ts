export type Role = "PLATFORM_ADMIN" | "MERCHANT" | "FINANCE_MANAGER";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  created_at: string;
  updated_at: string;
}

export interface Business {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface BusinessWithRole extends Business {
  my_role: "OWNER" | "FINANCE_MANAGER";
}

export interface BusinessesResponse {
  businesses: BusinessWithRole[];
}

export type BusinessMemberRole = "OWNER" | "FINANCE_MANAGER";

export interface BusinessMember {
  id: string;
  business_id: string;
  user_id: string;
  email: string | null;
  full_name: string | null;
  role: BusinessMemberRole;
  created_at: string;
}

export interface BusinessMembersResponse {
  business_id: string;
  members: BusinessMember[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
}

export interface UsersResponse {
  users: User[];
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
  business_id: string | null;
  name: string;
  account_type: AccountType;
  currency: string;
  current_balance: string;
  created_at: string;
  updated_at: string;
}

export interface AccountsResponse {
  user_id: string;
  accounts: Account[];
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

export interface TransactionsResponse {
  user_id: string;
  transactions: Transaction[];
}

export type CategoryType = "income" | "expense";

export interface Category {
  id: string;
  user_id: string | null;
  name: string;
  category_type: CategoryType;
  created_at: string;
}

export interface CategoriesResponse {
  user_id: string;
  categories: Category[];
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
  /** Present on the budgets list endpoint. */
  spent?: string;
  remaining?: string;
  progress_percent?: string;
}

export interface BudgetsResponse {
  user_id: string;
  budgets: Budget[];
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

export interface FinancialGoalsResponse {
  user_id: string;
  financial_goals: FinancialGoal[];
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

export interface SpendingByCategoryFact {
  category: string;
  amount: string;
}

export interface FinancialFactsBudget {
  id: string;
  category_id: string | null;
  amount: string;
  period: BudgetPeriod;
  start_date: string;
  end_date: string;
}

export interface FinancialFactsGoal {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  progress_percent: string;
  target_date: string | null;
  status: GoalStatus;
}

export interface FinancialFacts {
  total_income: string;
  total_expenses: string;
  net_cash_flow: string;
  transaction_count: number;
  income_transaction_count: number;
  expense_transaction_count: number;
  account_balance: string;
  spending_by_category: SpendingByCategoryFact[];
  budgets: FinancialFactsBudget[];
  financial_goals: FinancialFactsGoal[];
}

export interface FinancialExplanationResponse {
  answer: string;
}

export type RiskSeverity = "low" | "medium" | "high";

export type RecommendationPriority = "low" | "medium" | "high";

export interface RiskSignal {
  type: string;
  severity: RiskSeverity;
  summary: string;
  reason: string;
  explainable: boolean;
  transaction_ids: string[];
  amount: string | null;
}

export interface RiskIntelligenceResponse {
  user_id: string;
  signals: RiskSignal[];
}

export interface RecommendationMetric {
  name: string;
  value: string;
  threshold: string;
}

export interface FinancialRecommendation {
  priority: RecommendationPriority;
  type: string;
  title: string;
  body: string;
  grounded_amount: string;
  metric: RecommendationMetric;
}

export interface RecommendationsResponse {
  user_id: string;
  recommendations: FinancialRecommendation[];
}

export interface ControllerAction {
  action_type: string;
  description: string;
  severity: "info" | "low" | "medium" | "high";
  metadata: Record<string, unknown>;
}

export interface SourceFacts {
  money_values: Record<string, string>;
  extra: {
    financial_context?: {
      summary?: {
        total_income?: string;
        total_expenses?: string;
        net_cash_flow?: string;
        account_balance?: string;
      };
      activity?: {
        transaction_count?: number;
        income_transaction_count?: number;
        expense_transaction_count?: number;
      };
      spending_by_category?: unknown[];
      budgets?: unknown[];
      financial_goals?: unknown[];
    };
    risk_signals?: RiskSignal[];
    recommendations?: FinancialRecommendation[];
    cited_facts?: string[];
  };
}

export interface FinancialControllerReport {
  user_id: string;
  intent: string;
  source_facts: SourceFacts;
  decision: string;
  rationale: string;
  confidence: number;
  actions: ControllerAction[];
  created_at: string;
}

export interface AsyncTaskSubmitResponse {
  task_id: string;
  status: "PENDING";
}

export type AuditKind = "risk" | "recommendation" | "decision" | "reconciliation";

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
  result?: FinancialControllerReport | ReconciliationReport;
  message?: string;
}

export interface MatchRecord {
  statement_line_id: string;
  statement_amount: string;
  statement_date: string;
  statement_description: string;
  matched_transaction_id: string;
  match_basis: string;
}

export interface ReconciliationException {
  statement_line_id: string;
  statement_amount: string;
  statement_date: string;
  statement_description: string;
  category: string;
  review_status: string;
  reason: string;
}

export interface ReconciliationReport {
  user_id: string;
  source: string;
  batch_size: number;
  matched_count: number;
  match_rate: string;
  ledger_matched_count: number;
  exception_count: number;
  exception_rate: string;
  processing_duration_seconds: number;
  throughput: number;
  matched: MatchRecord[];
  exceptions: ReconciliationException[];
  created_at: string;
}

export interface ReconciliationLineReview {
  statement_line_id: string;
  review_status: string;
}

export interface ReconciliationExplainResponse {
  statement_line_id: string;
  category: string;
  explanation: string;
  suggested_resolution: string;
  is_proposal: boolean;
}
