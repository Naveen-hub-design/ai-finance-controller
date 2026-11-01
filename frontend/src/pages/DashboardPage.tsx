import { ComponentProps, useCallback, useEffect, useRef, useState } from "react";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Activity,
  Sparkles,
  ShieldAlert,
  ThumbsUp,
  Landmark,
  ArrowLeftRight,
  Clock,
  RefreshCw,
  Loader2,
  RotateCcw,
  ReceiptText,
  HeartPulse,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";

import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type { FinancialSummary, Transaction, TransactionsResponse } from "../lib/types";
import {
  formatCurrency,
  formatNumber,
  formatCompactCurrency,
  formatDate,
} from "../lib/format";
import { cn } from "../lib/cn";
import { transactionTypeLabels } from "../lib/labels";

const INCOME_COLOR = "#34d399";
const EXPENSE_COLOR = "#f87171";

type LoadState =
  | { status: "loading" }
  | { status: "success"; summary: FinancialSummary }
  | { status: "error"; message: string };

type RecentState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; transactions: Transaction[] }
  | { status: "error" };

function toNumberSafely(
  value: string | number | null | undefined
): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function MetricCard({
  label,
  icon,
  hint,
  value,
  iconClassName,
  valueClassName,
}: {
  label: string;
  icon: ComponentProps<typeof StatCard>["icon"];
  hint: string;
  value: ComponentProps<typeof StatCard>["value"];
  iconClassName?: string;
  valueClassName?: string;
}) {
  return (
    <StatCard
      label={label}
      icon={icon}
      value={
        <span className={cn("tabular-nums", valueClassName)}>{value}</span>
      }
      hint={hint}
      iconClassName={iconClassName}
    />
  );
}

interface ChartTooltipItem {
  name?: string | number;
  value?: number | string;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: ChartTooltipItem[];
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
  return (
    <div className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm shadow-card">
      <span className="text-muted">{String(item.name)}: </span>
      <span className="font-semibold text-foreground">
        {formatCurrency(item.value)}
      </span>
    </div>
  );
}

function InsightCard({
  icon: Icon,
  label,
  badgeText,
  badgeTone = "neutral",
  body,
  ctaLabel,
  ctaIcon: CtaIcon,
  to,
  variant = "primary",
  iconClassName,
}: {
  icon: typeof Sparkles;
  label: string;
  badgeText: string;
  badgeTone?: ComponentProps<typeof Badge>["tone"];
  body: string;
  ctaLabel: string;
  ctaIcon: typeof Sparkles;
  to: string;
  variant?: "primary" | "secondary" | "ghost";
  iconClassName?: string;
}) {
  return (
    <Card className="card-interactive">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface-raised text-accent-400",
            iconClassName
          )}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted">{label}</p>
          <Badge tone={badgeTone} className="mt-1.5">
            {badgeText}
          </Badge>
        </div>
      </div>
      <p className="mt-3.5 text-sm leading-relaxed text-muted">{body}</p>
      <Link to={to} className="mt-4 block">
        <Button variant={variant} size="sm" className="w-full">
          <CtaIcon className="h-4 w-4" aria-hidden="true" />
          {ctaLabel}
        </Button>
      </Link>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { businessQuery, selectedBusiness, isBusinessScope } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [recent, setRecent] = useState<RecentState>({ status: "idle" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);

  const loadRecent = useCallback(async () => {
    if (!user) return;
    setRecent({ status: "loading" });
    try {
      const q = businessQuery();
      const url = `/users/${user.id}/transactions${q}${q ? "&" : "?"}page_size=5`;
      const res = await api.get<TransactionsResponse>(url);
      if (cancelledRef.current) return;
      setRecent({ status: "success", transactions: res.transactions ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      setRecent({ status: "error" });
    }
  }, [user, businessQuery]);

  const load = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view your financial summary.",
      });
      return;
    }

    cancelledRef.current = false;
    setState({ status: "loading" });

    try {
      const summary = await api.get<FinancialSummary>(
        `/financial-summary/${user.id}${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", summary });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to load your financial summary.",
      });
    }
  }, [user, businessQuery]);

  useEffect(() => {
    cancelledRef.current = false;
    load();
    loadRecent();
    return () => {
      cancelledRef.current = true;
    };
  }, [load, loadRecent]);

  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const summary = await api.get<FinancialSummary>(
        `/financial-summary/${user.id}${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", summary });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to refresh your financial summary.",
      });
    } finally {
      if (!cancelledRef.current) setRefreshing(false);
    }
    loadRecent();
  }, [user, businessQuery, loadRecent]);

  const summary = state.status === "success" ? state.summary : null;

  const incomeN = summary ? (toNumberSafely(summary.total_income) ?? 0) : 0;
  const expensesN = summary ? (toNumberSafely(summary.total_expenses) ?? 0) : 0;
  const netN = summary ? (toNumberSafely(summary.net_cash_flow) ?? 0) : 0;
  const balanceN = summary ? (toNumberSafely(summary.account_balance) ?? 0) : 0;
  const txCount = summary ? summary.transaction_count : 0;
  const incomeTxCount = summary ? summary.income_transaction_count : 0;
  const expenseTxCount = summary ? summary.expense_transaction_count : 0;

  const hasActivity =
    state.status === "success" &&
    (txCount > 0 ||
      balanceN !== 0 ||
      incomeN !== 0 ||
      expensesN !== 0 ||
      netN !== 0);

  const chartData = [
    { name: "Income", value: incomeN, color: INCOME_COLOR },
    { name: "Expenses", value: expensesN, color: EXPENSE_COLOR },
  ];

  const netTone =
    netN > 0
      ? "text-success-500"
      : netN < 0
        ? "text-danger-400"
        : "text-warning-500";

  let health: {
    tone: ComponentProps<typeof Badge>["tone"];
    label: string;
    message: string;
  };
  if (!hasActivity) {
    health = {
      tone: "neutral",
      label: "No activity yet",
      message:
        "Record income and expenses to see a cash-flow assessment here.",
    };
  } else if (netN > 0) {
    health = {
      tone: "success",
      label: "Positive cash flow",
      message: `Income exceeds expenses by ${formatCurrency(netN)}, so your spending is currently staying within what you earn.`,
    };
  } else if (netN < 0) {
    health = {
      tone: "danger",
      label: "Negative cash flow",
      message: `Expenses exceed income by ${formatCurrency(-netN)}. This means you are spending more than you bring in during this period.`,
    };
  } else {
    health = {
      tone: "warning",
      label: "Balanced",
      message:
        "Income and expenses are equal, resulting in a net cash flow of zero.",
    };
  }

  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-border bg-surface px-6 py-5 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-accent-500">Financial Control Center</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground">
              {isBusinessScope && selectedBusiness ? selectedBusiness.name : "Dashboard"}
            </h1>
            <p className="mt-1 text-sm text-muted">
              {isBusinessScope ? "AI-powered financial control for your business — real-time overview of cash flow, budgets, risks and reconciliation." : "A high-level view of your financial health, upcoming obligations, and key metrics."}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link to="/transactions"><Button variant="secondary" size="sm"><ArrowLeftRight className="h-4 w-4" aria-hidden="true" />Add transaction</Button></Link>
            <Link to="/reconcile"><Button variant="secondary" size="sm"><Activity className="h-4 w-4" aria-hidden="true" />Run reconciliation</Button></Link>
            <Link to="/ai-controller"><Button size="sm"><Sparkles className="h-4 w-4" aria-hidden="true" />AI Controller</Button></Link>
            <Button variant="secondary" size="sm" onClick={refresh} disabled={refreshing || state.status === "loading"} title="Refresh financial summary">
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />Refresh
            </Button>
          </div>
        </div>
      </div>

      <section
        aria-label="Key metrics"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
      >
        <MetricCard
          label="Total Balance"
          icon={Wallet}
          hint="Sum of all account balances"
          iconClassName="text-accent-400"
          value={
            state.status === "success" ? formatCurrency(balanceN) : "—"
          }
        />
        <MetricCard
          label="Income"
          icon={TrendingUp}
          hint="Total income recorded"
          iconClassName="text-success-500"
          value={
            state.status === "success" ? formatCurrency(incomeN) : "—"
          }
        />
        <MetricCard
          label="Expenses"
          icon={TrendingDown}
          hint="Total expenses recorded"
          iconClassName="text-danger-400"
          value={
            state.status === "success" ? formatCurrency(expensesN) : "—"
          }
        />
        <MetricCard
          label="Net Cash Flow"
          icon={Activity}
          hint="Income minus expenses"
          iconClassName="text-warning-500"
          valueClassName={netTone}
          value={
            state.status === "success" ? formatCurrency(netN) : "—"
          }
        />
        <MetricCard
          label="Transactions"
          icon={ReceiptText}
          hint="Total transactions recorded"
          iconClassName="text-accent-400"
          value={
            state.status === "success"
              ? formatNumber(txCount, 0)
              : "—"
          }
        />
      </section>

      {state.status === "loading" && (
        <Card className="flex items-center gap-3 p-6">
          <Loader2
            className="h-5 w-5 animate-spin text-accent-400"
            aria-hidden="true"
          />
          <p className="text-sm text-muted">Loading your financial summary…</p>
        </Card>
      )}

      {state.status === "error" && (
        <EmptyState
          icon={Activity}
          title="Could not load financial summary"
          description={state.message}
          action={
            <Button variant="secondary" size="sm" onClick={load}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Retry
            </Button>
          }
        />
      )}

      {state.status === "success" && (
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <section aria-labelledby="overview-heading">
              <SectionHeading
                id="overview-heading"
                title="Financial Overview"
                description="A breakdown of total income versus total expenses recorded so far."
              />
              <Card className="mt-4">
                {incomeN + expensesN > 0 ? (
                  <div className="flex flex-col items-center gap-4 md:flex-row md:items-center md:justify-between">
                    <div
                      className="h-64 w-full max-w-xs"
                      role="img"
                      aria-label={`Income vs expenses chart: income ${formatCurrency(
                        incomeN
                      )}, expenses ${formatCurrency(expensesN)}`}
                    >
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={chartData}
                            dataKey="value"
                            nameKey="name"
                            innerRadius={60}
                            outerRadius={92}
                            paddingAngle={3}
                            strokeWidth={2}
                          >
                            {chartData.map((entry) => (
                              <Cell key={entry.name} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip content={<ChartTooltip />} />
                          <Legend
                            formatter={(value) => (
                              <span className="text-sm text-muted">{value}</span>
                            )}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid w-full max-w-xs grid-cols-2 gap-3">
                      <div className="rounded-lg bg-surface-raised/40 p-3">
                        <p className="text-xs text-muted">Income</p>
                        <p className="mt-1 truncate text-base font-semibold tabular-nums text-success-500">
                          {formatCompactCurrency(incomeN)}
                        </p>
                      </div>
                      <div className="rounded-lg bg-surface-raised/40 p-3">
                        <p className="text-xs text-muted">Expenses</p>
                        <p className="mt-1 truncate text-base font-semibold tabular-nums text-danger-400">
                          {formatCompactCurrency(expensesN)}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <EmptyState
                    icon={Activity}
                    title="No income or expense data yet"
                    description="Once transactions are recorded, an income versus expense breakdown will appear here."
                  />
                )}
              </Card>
            </section>

            <section aria-labelledby="financial-health-heading">
              <SectionHeading
                id="financial-health-heading"
                title="Financial Health"
                description="A deterministic assessment based on your recorded cash flow."
              />
              <Card
                className={cn(
                  "mt-4 border",
                  health.tone === "success" &&
                    "border-success-500/25 bg-success-500/5",
                  health.tone === "danger" &&
                    "border-danger-500/25 bg-danger-500/5",
                  health.tone === "warning" &&
                    "border-warning-500/25 bg-warning-500/5",
                  health.tone === "neutral" &&
                    "border-border-strong bg-surface-raised/30"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                    <HeartPulse className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-medium text-foreground">
                        Cash flow status
                      </h3>
                      <Badge tone={health.tone}>{health.label}</Badge>
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">
                      {health.message}
                    </p>
                    {hasActivity && (
                      <div className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                        <div>
                          <p className="text-xs text-muted">Income count</p>
                          <p className="mt-0.5 font-medium tabular-nums text-foreground">
                            {formatNumber(incomeTxCount, 0)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted">Expense count</p>
                          <p className="mt-0.5 font-medium tabular-nums text-foreground">
                            {formatNumber(expenseTxCount, 0)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted">Total transactions</p>
                          <p className="mt-0.5 font-medium tabular-nums text-foreground">
                            {formatNumber(txCount, 0)}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            </section>

            <section aria-labelledby="recent-activity-heading">
              <SectionHeading
                id="recent-activity-heading"
                title="Recent Activity"
                description="Your latest transactions at a glance."
                action={
                  <Link to="/transactions">
                    <Button variant="secondary" size="sm">
                      <ArrowLeftRight className="h-4 w-4" aria-hidden="true" />
                      View transactions
                    </Button>
                  </Link>
                }
              />
              <div className="mt-4">
                {recent.status === "loading" && (
                  <Card className="flex items-center justify-center gap-2.5 py-8 text-muted">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    <span className="text-sm">Loading recent transactions…</span>
                  </Card>
                )}
                {recent.status === "error" && (
                  <EmptyState
                    icon={Clock}
                    title="Could not load recent activity"
                    description="A temporary error prevented the recent activity feed from loading."
                  />
                )}
                {recent.status === "success" && recent.transactions.length === 0 && (
                  <EmptyState
                    icon={Clock}
                    title="No recent activity"
                    description="Transactions you record will show up here as the latest activity."
                  />
                )}
                {recent.status === "success" && recent.transactions.length > 0 && (
                  <Card className="overflow-hidden p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[520px] text-left text-sm">
                        <thead>
                          <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-faint">
                            <th scope="col" className="px-4 py-2.5 font-medium">Date</th>
                            <th scope="col" className="px-4 py-2.5 font-medium">Description</th>
                            <th scope="col" className="px-4 py-2.5 font-medium text-right">Amount</th>
                            <th scope="col" className="px-4 py-2.5 font-medium">Type</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {recent.transactions.map((tx) => {
                            const amt = toNumberSafely(tx.amount) ?? 0;
                            const isExpense = tx.transaction_type === "expense";
                            return (
                              <tr key={tx.id} className="hover:bg-surface-raised/40">
                                <td className="px-4 py-2 text-xs text-muted-faint">
                                  {formatDate(tx.transaction_date)}
                                </td>
                                <td className="px-4 py-2">
                                  <span className="truncate text-sm text-foreground">
                                    {tx.description || "Untitled"}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-right text-sm tabular-nums">
                                  <span className={cn(isExpense ? "text-danger-400" : "text-success-500")}>
                                    {isExpense ? "−" : "+"}{formatCurrency(amt)}
                                  </span>
                                </td>
                                <td className="px-4 py-2">
                                  <Badge tone={isExpense ? "danger" : "success"}>
                                    {transactionTypeLabels[tx.transaction_type]}
                                  </Badge>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                )}
              </div>
            </section>
          </div>

          <aside className="space-y-6" aria-label="AI and financial insights">
            <InsightCard
              icon={Landmark}
              label="Accounts"
              badgeText="Manage accounts"
              body="Link your accounts to start tracking balances and transactions."
              ctaLabel="Manage accounts"
              ctaIcon={Landmark}
              to="/accounts"
              variant="secondary"
            />

            <InsightCard
              icon={Sparkles}
              label="AI Controller"
              badgeText="Ask the AI controller"
              body="Ask the AI controller for a report on your finances."
              ctaLabel="Ask the controller"
              ctaIcon={Sparkles}
              to="/ai-controller"
              variant="primary"
            />

            <InsightCard
              icon={ShieldAlert}
              label="Risks"
              badgeText="Review risk signals"
              body="Anomalies and risk signals will be surfaced here."
              ctaLabel="Review risks"
              ctaIcon={ShieldAlert}
              to="/risks"
              variant="ghost"
              iconClassName="text-danger-400"
            />

            <InsightCard
              icon={ThumbsUp}
              label="Recommendations"
              badgeText="View suggestions"
              body="Actionable suggestions to improve your finances will appear here."
              ctaLabel="View recommendations"
              ctaIcon={ThumbsUp}
              to="/recommendations"
              variant="ghost"
              iconClassName="text-success-500"
            />
          </aside>
        </section>
      )}
    </div>
  );
}
