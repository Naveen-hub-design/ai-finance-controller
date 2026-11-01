import type {
  AccountType,
  AuditKind,
  BudgetPeriod,
  GoalStatus,
  RecommendationPriority,
  RiskSeverity,
  TransactionType,
} from "./types";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

export const accountTypeLabels: Record<AccountType, string> = {
  bank: "Bank",
  cash: "Cash",
  credit_card: "Credit Card",
  investment: "Investment",
  loan: "Loan",
  other: "Other",
};

export const transactionTypeLabels: Record<TransactionType, string> = {
  income: "Income",
  expense: "Expense",
  transfer: "Transfer",
};

export const transactionTypeTones: Record<TransactionType, Tone> = {
  income: "success",
  expense: "danger",
  transfer: "accent",
};

export const goalStatusLabels: Record<GoalStatus, string> = {
  active: "Active",
  completed: "Completed",
  paused: "Paused",
  cancelled: "Cancelled",
};

export const goalStatusTones: Record<GoalStatus, Tone> = {
  active: "accent",
  completed: "success",
  paused: "warning",
  cancelled: "neutral",
};

export const budgetPeriodLabels: Record<BudgetPeriod, string> = {
  weekly: "Weekly",
  monthly: "Monthly",
  yearly: "Yearly",
};

export const riskSeverityLabels: Record<RiskSeverity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const riskSeverityTones: Record<RiskSeverity, Tone> = {
  low: "neutral",
  medium: "warning",
  high: "danger",
};

export const recommendationPriorityLabels: Record<RecommendationPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const recommendationPriorityTones: Record<RecommendationPriority, Tone> = {
  low: "success",
  medium: "warning",
  high: "danger",
};

export const auditKindLabels: Record<AuditKind, string> = {
  decision: "Decision",
  risk: "Risk",
  recommendation: "Recommendation",
  reconciliation: "Reconciliation",
};

export const auditKindTones: Record<AuditKind, Tone> = {
  decision: "accent",
  risk: "danger",
  recommendation: "success",
  reconciliation: "accent",
};

export const budgetStatusTones: Record<string, Tone> = {
  on_track: "success",
  near_limit: "warning",
  over: "danger",
  upcoming: "neutral",
};

const NEAR_LIMIT_THRESHOLD = 80;
const OVER_THRESHOLD = 100;

/** Canonical budget grading shared by every page that renders budgets. */
export function budgetStatusFromProgress(
  progress: number | null
): keyof typeof budgetStatusTones {
  if (progress === null || progress < 0) return "upcoming";
  if (progress >= OVER_THRESHOLD) return "over";
  if (progress >= NEAR_LIMIT_THRESHOLD) return "near_limit";
  return "on_track";
}

export function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
