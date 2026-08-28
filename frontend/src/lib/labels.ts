import type {
  AccountType,
  AuditKind,
  BudgetPeriod,
  GoalStatus,
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

export const auditKindLabels: Record<AuditKind, string> = {
  decision: "Decision",
  risk: "Risk",
  recommendation: "Recommendation",
};

export const auditKindTones: Record<AuditKind, Tone> = {
  decision: "accent",
  risk: "danger",
  recommendation: "success",
};

export const budgetStatusTones: Record<string, Tone> = {
  on_track: "success",
  near_limit: "warning",
  over: "danger",
  upcoming: "neutral",
};

export function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
