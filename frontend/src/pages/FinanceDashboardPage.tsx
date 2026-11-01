import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ComponentProps,
} from "react";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  ShieldAlert,
  ThumbsUp,
  PiggyBank,
  ArrowLeftRight,
  Loader2,
  RefreshCw,
  RotateCcw,
  Target,
  ReceiptText,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { EmptyState } from "../components/ui/EmptyState";
import { ForbiddenState } from "../components/ui/ForbiddenState";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type {
  FinancialSummary,
  Budget,
  BudgetsResponse,
  RiskSignal,
  RiskIntelligenceResponse,
  FinancialRecommendation,
  RecommendationsResponse,
} from "../lib/types";
import {
  riskSeverityLabels,
  riskSeverityTones,
  recommendationPriorityLabels,
  recommendationPriorityTones,
  budgetPeriodLabels,
  budgetStatusFromProgress,
} from "../lib/labels";
import {
  formatCurrency,
  formatNumber,
  formatPercent,
} from "../lib/format";
import { cn } from "../lib/cn";

const INCOME_TONE = "text-success-500";
const EXPENSE_TONE = "text-danger-400";

function toNumberSafely(
  value: string | number | null | undefined
): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function Metric({
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
  value: React.ReactNode;
  iconClassName?: string;
  valueClassName?: string;
}) {
  return (
    <StatCard
      label={label}
      icon={icon}
      value={<span className={cn("tabular-nums", valueClassName)}>{value}</span>}
      hint={hint}
      iconClassName={iconClassName}
    />
  );
}

type SummaryState =
  | { status: "loading" }
  | { status: "success"; summary: FinancialSummary }
  | { status: "error"; message: string }
  | { status: "forbidden" };

type ListState<T> =
  | { status: "loading" }
  | { status: "success"; items: T[] }
  | { status: "error"; message: string }
  | { status: "forbidden" };

function forbiddenMessage(err: unknown, fallback: string): string {
  const e = err as ApiError;
  return e.status === 403 ? "forbidden" : e.message || fallback;
}

export default function FinanceDashboardPage() {
  const { user } = useAuth();
  const { businessQuery, isBusinessScope } = useBusiness();

  const [summary, setSummary] = useState<SummaryState>({ status: "loading" });
  const [budgets, setBudgets] = useState<ListState<Budget>>({
    status: "loading",
  });
  const [risks, setRisks] = useState<ListState<RiskSignal>>({
    status: "loading",
  });
  const [recommendations, setRecommendations] = useState<
    ListState<FinancialRecommendation>
  >({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);

  const uid = user?.id;

  const loadAll = useCallback(async () => {
    if (!uid) return;
    cancelledRef.current = false;

    setSummary({ status: "loading" });
    setBudgets({ status: "loading" });
    setRisks({ status: "loading" });
    setRecommendations({ status: "loading" });

    const q = businessQuery();

    const listError = <T,>(
      setter: (s: ListState<T>) => void
    ) => (msg: string) => {
      if (msg === "forbidden") {
        setter({ status: "forbidden" });
      } else {
        setter({ status: "error", message: msg });
      }
    };

    const run = async <T,>(
      fetchFn: () => Promise<T>,
      apply: (s: T) => void,
      onError: (msg: string) => void = (msg) => {
        if (msg === "forbidden") {
          setSummary({ status: "forbidden" });
        } else {
          setSummary({ status: "error", message: msg });
        }
      }
    ) => {
      try {
        const res = await fetchFn();
        if (!cancelledRef.current) apply(res);
      } catch (err: unknown) {
        if (cancelledRef.current) return;
        onError(forbiddenMessage(err, "Unable to load data."));
      }
    };

    await run(
      () => api.get<FinancialSummary>(`/financial-summary/${uid}${q}`),
      (s) => setSummary({ status: "success", summary: s })
    );
    await run(
      () => api.get<BudgetsResponse>(`/users/${uid}/budgets${q}`),
      (res) => setBudgets({ status: "success", items: res.budgets ?? [] }),
      listError(setBudgets)
    );
    await run(
      () => api.get<RiskIntelligenceResponse>(`/users/${uid}/risk-intelligence${q}`),
      (res) => setRisks({ status: "success", items: res.signals ?? [] }),
      listError(setRisks)
    );
    await run(
      () => api.get<RecommendationsResponse>(`/users/${uid}/recommendations${q}`),
      (res) =>
        setRecommendations({ status: "success", items: res.recommendations ?? [] }),
      listError(setRecommendations)
    );
  }, [uid, businessQuery]);

  useEffect(() => {
    loadAll();
    return () => {
      cancelledRef.current = true;
    };
  }, [loadAll]);

  const refresh = useCallback(async () => {
    if (!uid) return;
    setRefreshing(true);
    await loadAll();
    setRefreshing(false);
  }, [uid, loadAll]);

  const s = summary.status === "success" ? summary.summary : null;
  const incomeN = s ? (toNumberSafely(s.total_income) ?? 0) : 0;
  const expensesN = s ? (toNumberSafely(s.total_expenses) ?? 0) : 0;
  const netN = s ? (toNumberSafely(s.net_cash_flow) ?? 0) : 0;
  const balanceN = s ? (toNumberSafely(s.account_balance) ?? 0) : 0;
  const txCount = s ? s.transaction_count : 0;

  const riskItems = risks.status === "success" ? risks.items : [];
  const highRiskCount = riskItems.filter((r) => r.severity === "high").length;
  const recItems =
    recommendations.status === "success" ? recommendations.items : [];
  const highRecCount = recItems.filter((r) => r.priority === "high").length;
  const budgetItems = budgets.status === "success" ? budgets.items : [];
  const onTrackBudgets = budgetItems.filter(
    (b) =>
      toNumberSafely(b.progress_percent) !== null &&
      budgetStatusFromProgress(toNumberSafely(b.progress_percent)) ===
        "on_track"
  ).length;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Finance Dashboard"
        description="Financial operations and analysis across the businesses you manage."
        actions={
          <Button
            variant="secondary"
            onClick={refresh}
            disabled={refreshing}
            title="Refresh financial data"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </Button>
        }
      />

      <section aria-label="Key operations metrics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Total Balance"
          icon={Wallet}
          hint="Across selected accounts"
          iconClassName="text-accent-400"
          value={summary.status === "success" ? formatCurrency(balanceN) : "—"}
        />
        <Metric
          label="Income"
          icon={TrendingUp}
          hint="Recorded income"
          iconClassName="text-success-500"
          valueClassName={INCOME_TONE}
          value={summary.status === "success" ? formatCurrency(incomeN) : "—"}
        />
        <Metric
          label="Expenses"
          icon={TrendingDown}
          hint="Recorded expenses"
          iconClassName="text-danger-400"
          valueClassName={EXPENSE_TONE}
          value={summary.status === "success" ? formatCurrency(expensesN) : "—"}
        />
        <Metric
          label="Net Cash Flow"
          icon={Activity}
          hint="Income minus expenses"
          iconClassName="text-warning-500"
          value={summary.status === "success" ? formatCurrency(netN) : "—"}
        />
      </section>

      {summary.status === "loading" && (
        <Card className="flex items-center gap-3 p-6">
          <Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" />
          <p className="text-sm text-muted">Loading financial data…</p>
        </Card>
      )}

      {summary.status === "forbidden" && (
        <ForbiddenState />
      )}

      {summary.status === "error" && (
        <EmptyState
          icon={Activity}
          title="Could not load financial data"
          description={summary.message}
          action={
            <Button variant="secondary" size="sm" onClick={loadAll}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Retry
            </Button>
          }
        />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="space-y-6 lg:col-span-2" aria-label="Operational analysis">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Metric
              label="Transactions processed"
              icon={ReceiptText}
              hint="Total transactions in scope"
              iconClassName="text-accent-400"
              value={summary.status === "success" ? formatNumber(txCount, 0) : "—"}
            />
            <Metric
              label="High-priority risks"
              icon={ShieldAlert}
              hint="Flagged for review"
              iconClassName="text-danger-400"
              value={risks.status === "success" ? formatNumber(highRiskCount, 0) : "—"}
            />
            <Metric
              label="Budgets on track"
              icon={PiggyBank}
              hint="Under 80% of budget used"
              iconClassName="text-success-500"
              value={budgets.status === "success" ? formatNumber(onTrackBudgets, 0) : "—"}
            />
            <Metric
              label="High-priority actions"
              icon={ThumbsUp}
              hint="Recommendations to apply"
              iconClassName="text-warning-500"
              value={recommendations.status === "success" ? formatNumber(highRecCount, 0) : "—"}
            />
          </div>

          <section aria-labelledby="budget-tracking-heading">
            <div className="mb-4 flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                <PiggyBank className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <h2 id="budget-tracking-heading" className="text-sm font-semibold tracking-tight text-foreground">
                  Budget tracking
                </h2>
                <p className="text-xs text-muted-faint">
                  Spend vs. budget across active periods.
                </p>
              </div>
            </div>
            {budgets.status === "loading" && (
              <Card><p className="text-sm text-muted">Loading budgets…</p></Card>
            )}
            {budgets.status === "forbidden" && <ForbiddenState />}
            {budgets.status === "error" && (
              <EmptyState icon={PiggyBank} title="Could not load budgets" description={budgets.message} />
            )}
            {budgets.status === "success" && (
              <Card>
                {budgetItems.length === 0 ? (
                  <EmptyState
                    icon={PiggyBank}
                    title="No budgets yet"
                    description="Budgets you put in place will be tracked here."
                  />
                ) : (
                  <ul className="divide-y divide-border">
                    {budgetItems.slice(0, 5).map((b) => {
                      const spent = toNumberSafely(b.spent) ?? 0;
                      const amount = toNumberSafely(b.amount) ?? 0;
                      const progress = toNumberSafely(b.progress_percent) ?? 0;
                      const pct = amount > 0 ? Math.min(progress, 100) : 0;
                      const status = budgetStatusFromProgress(
                        toNumberSafely(b.progress_percent)
                      );
                      const over = status === "over";
                      const nearLimit = status === "near_limit";
                      return (
                        <li key={b.id} className="px-1 py-4 first:pt-1 last:pb-1">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-foreground">
                                {b.category_id ? "Category budget" : "Overall budget"}
                              </p>
                              <p className="text-xs text-muted-faint">
                                {budgetPeriodLabels[b.period]}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-semibold tabular-nums text-foreground">
                                {formatCurrency(spent)}
                                <span className="font-normal text-muted-faint"> / {formatCurrency(amount)}</span>
                              </p>
                              <p className={cn("text-xs font-medium", over ? "text-danger-400" : nearLimit ? "text-warning-500" : "text-muted-faint")}>
                                {formatPercent(progress)} used
                              </p>
                            </div>
                          </div>
                          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all",
                                over ? "bg-danger-500" : nearLimit ? "bg-warning-500" : "bg-accent-500"
                              )}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Card>
            )}
          </section>

          <section aria-labelledby="risk-signals-heading">
            <div className="mb-4 flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-danger-400">
                <ShieldAlert className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <h2 id="risk-signals-heading" className="text-sm font-semibold tracking-tight text-foreground">
                  Active risk signals
                </h2>
                <p className="text-xs text-muted-faint">
                  Anomalies to review across the operation.
                </p>
              </div>
            </div>
            {risks.status === "loading" && (
              <Card><p className="text-sm text-muted">Analyzing risk signals…</p></Card>
            )}
            {risks.status === "forbidden" && <ForbiddenState />}
            {risks.status === "error" && (
              <EmptyState icon={ShieldAlert} title="Could not load risk intelligence" description={risks.message} />
            )}
            {risks.status === "success" && (
              <Card>
                {riskItems.length === 0 ? (
                  <EmptyState
                    icon={ShieldAlert}
                    title="No risk signals"
                    description="No anomalies detected in the current scope."
                  />
                ) : (
                  <ul className="divide-y divide-border">
                    {riskItems.slice(0, 4).map((r, i) => (
                      <li key={i} className="flex items-start justify-between gap-3 px-1 py-3.5 first:pt-1 last:pb-1">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {r.summary || "Risk signal"}
                          </p>
                          <p className="text-xs text-muted-faint">{r.type}</p>
                        </div>
                        <Badge tone={riskSeverityTones[r.severity]}>
                          {riskSeverityLabels[r.severity]}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            )}
          </section>
        </section>

        <aside className="space-y-6" aria-label="Analysis and actions">
          <section aria-labelledby="scope-heading">
            <div className="mb-4 flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                <BarChart3 className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <h2 id="scope-heading" className="text-sm font-semibold tracking-tight text-foreground">
                  Analysis scope
                </h2>
                <p className="text-xs text-muted-faint">
                  Data shown follows your business selection.
                </p>
              </div>
            </div>
            <Card>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted">Scope</span>
                  <Badge tone={isBusinessScope ? "accent" : "neutral"}>
                    {isBusinessScope ? "Business" : "Personal"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Transactions</span>
                  <span className="font-medium tabular-nums text-foreground">
                    {summary.status === "success" ? formatNumber(txCount, 0) : "—"}
                  </span>
                </div>
              </div>
            </Card>
          </section>

          <section aria-labelledby="recommendations-heading">
            <div className="mb-4 flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-warning-500">
                <ThumbsUp className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <h2 id="recommendations-heading" className="text-sm font-semibold tracking-tight text-foreground">
                  Top recommendations
                </h2>
                <p className="text-xs text-muted-faint">
                  Highest-priority improvements.
                </p>
              </div>
            </div>
            {recommendations.status === "loading" && (
              <Card><p className="text-sm text-muted">Loading recommendations…</p></Card>
            )}
            {recommendations.status === "forbidden" && <ForbiddenState />}
            {recommendations.status === "error" && (
              <EmptyState icon={ThumbsUp} title="Could not load recommendations" description={recommendations.message} />
            )}
            {recommendations.status === "success" && (
              <Card>
                {recItems.length === 0 ? (
                  <EmptyState
                    icon={ThumbsUp}
                    title="No recommendations"
                    description="Suggestions will appear as patterns are detected."
                  />
                ) : (
                  <ul className="divide-y divide-border">
                    {recItems.slice(0, 4).map((r, i) => (
                      <li key={i} className="px-1 py-3.5 first:pt-1 last:pb-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-foreground">{r.title}</p>
                          <Badge tone={recommendationPriorityTones[r.priority]}>
                            {recommendationPriorityLabels[r.priority]}
                          </Badge>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">{r.body}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            )}
          </section>

          <section aria-labelledby="quick-links-heading" className="space-y-2">
            <h2 id="quick-links-heading" className="text-xs font-semibold uppercase tracking-wider text-muted-faint">
              Operations
            </h2>
            <Link to="/transactions">
              <Button variant="secondary" className="w-full justify-start">
                <ArrowLeftRight className="h-4 w-4" aria-hidden="true" />
                Review transactions
              </Button>
            </Link>
            <Link to="/budgets">
              <Button variant="secondary" className="w-full justify-start">
                <PiggyBank className="h-4 w-4" aria-hidden="true" />
                Manage budgets
              </Button>
            </Link>
            <Link to="/goals">
              <Button variant="secondary" className="w-full justify-start">
                <Target className="h-4 w-4" aria-hidden="true" />
                Track goals
              </Button>
            </Link>
            <Link to="/ai-analysis">
              <Button variant="secondary" className="w-full justify-start">
                <Sparkles className="h-4 w-4" aria-hidden="true" />
                AI financial analysis
              </Button>
            </Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
