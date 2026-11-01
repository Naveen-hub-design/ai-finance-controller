import { useCallback, useEffect, useRef, useState } from "react";
import {
  BrainCircuit,
  Sparkles,
  Send,
  CircleDollarSign,
  TrendingUp,
  TrendingDown,
  Wallet,
  Activity,
  ReceiptText,
  RefreshCw,
  Loader2,
  RotateCcw,
  PiggyBank,
  Target,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { Progress } from "../components/ui/Progress";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type {
  FinancialFacts,
  SpendingByCategoryFact,
  FinancialExplanationResponse,
} from "../lib/types";
import {
  formatCurrency,
  formatPercent,
  formatNumber,
} from "../lib/format";
import { cn } from "../lib/cn";

type LoadState =
  | { status: "loading" }
  | { status: "success"; facts: FinancialFacts }
  | { status: "error"; message: string };

type AskState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; answer: string }
  | { status: "error"; message: string };

const SUGGESTED_QUESTIONS = [
  "Why did my expenses increase?",
  "What are my biggest spending categories?",
  "How is my cash flow performing?",
  "Where could I reduce unnecessary spending?",
];

const GOAL_SUGGESTED_QUESTIONS = [
  "How is my progress toward my financial goals?",
  "Will I reach my goal target by its target date?",
  "What can I adjust to stay on track with my goal?",
  "Is my goal timeline realistic given my current finances?",
];

function toNumberSafely(
  value: string | number | null | undefined
): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function HealthCard({
  label,
  icon,
  hint,
  value,
  iconClassName,
  valueClassName,
}: {
  label: string;
  icon: LucideIcon;
  hint: string;
  value: string;
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

function CategoryBar({
  category,
  amount,
  totalExpenses,
}: {
  category: SpendingByCategoryFact;
  amount: number;
  totalExpenses: number;
}) {
  const share =
    totalExpenses > 0 ? (amount / totalExpenses) * 100 : 0;
  return (
    <li className="flex items-center justify-between gap-4 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate text-sm font-medium text-foreground">
            {category.category || "Uncategorized"}
          </span>
          <span className="text-sm tabular-nums text-muted">
            {formatPercent(share)}
          </span>
        </div>
        <div className="mt-1.5">
          <Progress value={share} tone="accent" />
        </div>
      </div>
      <span className="shrink-0 text-sm font-semibold tabular-nums text-foreground">
        {formatCurrency(amount)}
      </span>
    </li>
  );
}

const textareaClass =
  "w-full resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 hover:border-border-strong focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50";

export default function AiAnalysisPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [question, setQuestion] = useState("");
  const [askState, setAskState] = useState<AskState>({ status: "idle" });
  const [goalQuestion, setGoalQuestion] = useState("");
  const [goalAskState, setGoalAskState] = useState<AskState>({ status: "idle" });
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view your financial facts.",
      });
      return;
    }

    cancelledRef.current = false;
    setState({ status: "loading" });

    try {
      const facts = await api.get<FinancialFacts>(
        `/users/${user.id}/financial-facts${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", facts });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to load your financial facts.",
      });
    }
  }, [user, businessQuery]);

  useEffect(() => {
    load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const facts = await api.get<FinancialFacts>(
        `/users/${user.id}/financial-facts${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", facts });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to refresh your financial facts.",
      });
    } finally {
      if (!cancelledRef.current) setRefreshing(false);
    }
  }, [user, businessQuery]);

  const handleAsk = async () => {
    const q = question.trim();
    if (!q || !user) return;
    setAskState({ status: "loading" });
    try {
      const res = await api.post<FinancialExplanationResponse>(
        `/users/${user.id}/financial-explanation${businessQuery()}`,
        { question: q }
      );
      setAskState({
        status: "success",
        answer: res.answer ?? "No explanation was returned.",
      });
    } catch (err: unknown) {
      const e = err as ApiError;
      setAskState({
        status: "error",
        message: e.message || "Unable to get an explanation right now.",
      });
    }
  };

  const handleGoalAsk = async () => {
    const q = goalQuestion.trim();
    if (!q || !user) return;
    setGoalAskState({ status: "loading" });
    try {
      const res = await api.post<FinancialExplanationResponse>(
        `/users/${user.id}/financial-goal-intelligence${businessQuery()}`,
        { question: q }
      );
      setGoalAskState({
        status: "success",
        answer: res.answer ?? "No goal intelligence was returned.",
      });
    } catch (err: unknown) {
      const e = err as ApiError;
      setGoalAskState({
        status: "error",
        message: e.message || "Unable to analyze your goals right now.",
      });
    }
  };

  const facts = state.status === "success" ? state.facts : null;

  const incomeN = facts ? (toNumberSafely(facts.total_income) ?? 0) : 0;
  const expensesN = facts ? (toNumberSafely(facts.total_expenses) ?? 0) : 0;
  const netN = facts ? (toNumberSafely(facts.net_cash_flow) ?? 0) : 0;
  const balanceN = facts ? (toNumberSafely(facts.account_balance) ?? 0) : 0;
  const txCount = facts ? facts.transaction_count : 0;

  const netTone =
    netN > 0
      ? "text-success-500"
      : netN < 0
        ? "text-danger-400"
        : "text-warning-500";

  const spending = facts ? facts.spending_by_category : [];
  const budgetCount = facts ? facts.budgets.length : 0;
  const goalCount = facts ? facts.financial_goals.length : 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="AI Analysis"
        description="Deterministic financial intelligence computed from your recorded data."
        actions={
          <Button
            variant="secondary"
            onClick={refresh}
            disabled={refreshing || state.status === "loading"}
            title="Refresh financial facts"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </Button>
        }
      />

      <section aria-labelledby="health-overview-heading">
        <SectionHeading
          id="health-overview-heading"
          title="Financial Health Overview"
          description="Key financial indicators computed deterministically from your data."
          action={
            <Badge tone="accent">Deterministic</Badge>
          }
        />
        {state.status === "loading" && (
          <Card className="mt-4 flex items-center gap-3 p-6">
            <Loader2
              className="h-5 w-5 animate-spin text-accent-400"
              aria-hidden="true"
            />
            <p className="text-sm text-muted">Loading your financial facts…</p>
          </Card>
        )}

        {state.status === "error" && (
          <div className="mt-4">
            <EmptyState
              icon={CircleDollarSign}
              title="Could not load financial facts"
              description={state.message}
              action={
                <Button variant="secondary" size="sm" onClick={load}>
                  <RotateCcw className="h-4 w-4" aria-hidden="true" />
                  Retry
                </Button>
              }
            />
          </div>
        )}

        {state.status === "success" && (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <HealthCard
              label="Total Balance"
              icon={Wallet}
              hint="Sum of all account balances"
              iconClassName="text-accent-400"
              value={formatCurrency(balanceN)}
            />
            <HealthCard
              label="Total Income"
              icon={TrendingUp}
              hint="Total income recorded"
              iconClassName="text-success-500"
              value={formatCurrency(incomeN)}
            />
            <HealthCard
              label="Total Expenses"
              icon={TrendingDown}
              hint="Total expenses recorded"
              iconClassName="text-danger-400"
              value={formatCurrency(expensesN)}
            />
            <HealthCard
              label="Net Cash Flow"
              icon={Activity}
              hint="Income minus expenses"
              iconClassName="text-warning-500"
              valueClassName={netTone}
              value={formatCurrency(netN)}
            />
            <HealthCard
              label="Transactions"
              icon={ReceiptText}
              hint="Total transactions recorded"
              iconClassName="text-accent-400"
              value={formatNumber(txCount, 0)}
            />
          </div>
        )}
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-raised text-accent-400">
              <BrainCircuit className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-base font-semibold tracking-tight text-foreground">
                Ask AI about your finances
              </h3>
              <p className="text-sm text-muted">
                Get an explanation or insight from your financial data.
              </p>
            </div>
          </div>

          <div className="mt-4">
            <label htmlFor="ai-question" className="text-xs font-medium text-muted">
              Ask a question
            </label>
            <textarea
              id="ai-question"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void handleAsk();
                }
              }}
              placeholder="e.g. Explain my spending this month — which categories grew?"
              disabled={askState.status === "loading"}
              aria-describedby={
                askState.status === "error" ? "ai-error" : undefined
              }
              className={textareaClass}
            />
          </div>

          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-xs text-muted-faint">
              Press Ctrl/⌘ + Enter or click Ask.
            </p>
            <Button
              onClick={() => void handleAsk()}
              disabled={
                !question.trim() || askState.status === "loading"
              }
              aria-busy={askState.status === "loading"}
            >
              {askState.status === "loading" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="h-4 w-4" aria-hidden="true" />
              )}
              {askState.status === "loading" ? "Asking…" : "Ask"}
            </Button>
          </div>

          <div className="mt-4">
            <p className="text-xs font-medium text-muted">Try asking</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setQuestion(suggestion)}
                  disabled={askState.status === "loading"}
                  className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted transition-colors duration-150 hover:border-accent-500/50 hover:bg-surface-raised hover:text-foreground focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          <div aria-live="polite">
            {askState.status === "loading" && (
              <div className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-surface-raised p-4">
                <Loader2
                  className="h-5 w-5 animate-spin text-accent-400"
                  aria-hidden="true"
                />
                <p className="text-sm text-muted">
                  Analyzing your finances… this can take a few moments.
                </p>
              </div>
            )}

            {askState.status === "success" && (
              <div className="mt-4 rounded-lg border border-accent-500/25 bg-accent-500/5 p-4">
                <div className="flex items-center gap-2">
                  <Badge tone="accent">
                    <Sparkles className="h-3 w-3" aria-hidden="true" />
                    AI-generated
                  </Badge>
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                  {askState.answer}
                </p>
              </div>
            )}

            {askState.status === "error" && (
              <div
                id="ai-error"
                className="mt-4 rounded-lg border border-danger-400/25 bg-danger-400/5 p-4"
              >
                <div className="flex items-center gap-2">
                  <Badge tone="danger">Error</Badge>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  {askState.message}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => void handleAsk()}
                >
                  <RotateCcw className="h-4 w-4" aria-hidden="true" />
                  Retry
                </Button>
              </div>
            )}
          </div>
        </Card>

        <div className="space-y-4">
          <SectionHeading
            id="insights-heading"
            title="Insights"
            description="Generated observations about your financial patterns."
          />
          <Card className="border-warning-500/25 bg-warning-500/5">
            <div className="flex items-start gap-2.5">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-warning-500" aria-hidden="true" />
              <div className="text-sm leading-relaxed text-foreground">
                <p className="font-medium">AI-powered insights are not available</p>
                <p className="mt-1 text-muted">
                  The AI provider is not configured in this deployment. Set
                  <code className="mx-1 rounded bg-surface-raised px-1.5 py-0.5 text-xs">OPENAI_API_KEY</code>
                  in the API service environment and restart it to enable
                  natural-language financial explanations and insights.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <SectionHeading
            id="facts-heading"
            title="Financial Facts"
            description="Spending by category, broken down from your expense transactions."
          />
          {state.status === "success" && spending.length === 0 && (
            <div className="mt-4">
              <EmptyState
                icon={CircleDollarSign}
                title="No spending breakdown yet"
                description="Once expenses with categories are recorded, a per-category breakdown will appear here."
              />
            </div>
          )}
          {state.status === "success" && spending.length > 0 && (
            <>
              <p className="mt-2 text-xs text-muted-faint">
                {formatCurrency(expensesN)} total expenses across{" "}
                {spending.length} categor{spending.length === 1 ? "y" : "ies"}.
              </p>
              <ul className="mt-2 divide-y divide-border">
                {spending.map((category) => (
                  <CategoryBar
                    key={category.category}
                    category={category}
                    amount={toNumberSafely(category.amount) ?? 0}
                    totalExpenses={expensesN}
                  />
                ))}
              </ul>
            </>
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <SectionHeading
              id="snapshot-heading"
              title="Budget & Goal Snapshot"
              description="Counts derived from your current budgets and financial goals."
            />
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Link to="/budgets">
                <Button variant="secondary" className="w-full">
                  <PiggyBank className="h-4 w-4" aria-hidden="true" />
                  {formatNumber(budgetCount, 0)} budget
                  {budgetCount === 1 ? "" : "s"}
                </Button>
              </Link>
              <Link to="/goals">
                <Button variant="secondary" className="w-full">
                  <Target className="h-4 w-4" aria-hidden="true" />
                  {formatNumber(goalCount, 0)} goal
                  {goalCount === 1 ? "" : "s"}
                </Button>
              </Link>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-faint">
              Manage your budgets and financial goals on their dedicated pages.
            </p>
          </Card>

          <Card>
            <SectionHeading
              id="goal-intelligence-heading"
              title="Goal Intelligence"
              description="Understand whether your current financial trajectory supports your goals."
            />

            {state.status === "success" && goalCount === 0 && (
              <div className="mt-4">
                <EmptyState
                  icon={Target}
                  title="No financial goals yet"
                  description="Goal intelligence answers questions grounded in your financial goals. Create a goal to get grounded, data-driven analysis."
                  action={
                    <Link to="/goals">
                      <Button variant="secondary" size="sm">
                        <Target className="h-4 w-4" aria-hidden="true" />
                        Manage goals
                      </Button>
                    </Link>
                  }
                />
              </div>
            )}

            <div className="mt-4">
              <label
                htmlFor="goal-question"
                className="text-xs font-medium text-muted"
              >
                Ask about your goals
              </label>
              <textarea
                id="goal-question"
                rows={3}
                value={goalQuestion}
                onChange={(e) => setGoalQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    void handleGoalAsk();
                  }
                }}
                placeholder="e.g. Will my emergency fund reach its target by its deadline?"
                disabled={goalAskState.status === "loading"}
                aria-describedby={
                  goalAskState.status === "error" ? "goal-error" : undefined
                }
                className={textareaClass}
              />
            </div>

            <div className="mt-3 flex items-center justify-between gap-3">
              <p className="text-xs text-muted-faint">
                Press Ctrl/⌘ + Enter or click Ask.
              </p>
              <Button
                onClick={() => void handleGoalAsk()}
                disabled={
                  !goalQuestion.trim() || goalAskState.status === "loading"
                }
                aria-busy={goalAskState.status === "loading"}
              >
                {goalAskState.status === "loading" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Send className="h-4 w-4" aria-hidden="true" />
                )}
                {goalAskState.status === "loading" ? "Analyzing…" : "Ask"}
              </Button>
            </div>

            <div className="mt-4">
              <p className="text-xs font-medium text-muted">Try asking</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {GOAL_SUGGESTED_QUESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setGoalQuestion(suggestion)}
                    disabled={goalAskState.status === "loading"}
                    className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted transition-colors duration-150 hover:border-accent-500/50 hover:bg-surface-raised hover:text-foreground focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            <div aria-live="polite">
              {goalAskState.status === "loading" && (
                <div className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-surface-raised p-4">
                  <Loader2
                    className="h-5 w-5 animate-spin text-accent-400"
                    aria-hidden="true"
                  />
                  <p className="text-sm text-muted">
                    Analyzing your financial goals… this can take a few
                    moments.
                  </p>
                </div>
              )}

              {goalAskState.status === "success" && (
                <div className="mt-4 rounded-lg border border-accent-500/25 bg-accent-500/5 p-4">
                  <div className="flex items-center gap-2">
                    <Badge tone="accent">
                      <Sparkles className="h-3 w-3" aria-hidden="true" />
                      AI-generated
                    </Badge>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                    {goalAskState.answer}
                  </p>
                </div>
              )}

              {goalAskState.status === "error" && (
                <div
                  id="goal-error"
                  className="mt-4 rounded-lg border border-danger-400/25 bg-danger-400/5 p-4"
                >
                  <div className="flex items-center gap-2">
                    <Badge tone="danger">Error</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-muted">
                    {goalAskState.message}
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="mt-3"
                    onClick={() => void handleGoalAsk()}
                  >
                    <RotateCcw className="h-4 w-4" aria-hidden="true" />
                    Retry
                  </Button>
                </div>
              )}
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
