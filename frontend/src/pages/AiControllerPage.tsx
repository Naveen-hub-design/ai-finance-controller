import { useCallback, useEffect, useRef, useState, type ComponentProps } from "react";
import {
  Send,
  RotateCcw,
  Loader2,
  CheckCircle2,
  CircleX,
  BrainCircuit,
  ShieldAlert,
  ThumbsUp,
  Workflow,
  Sparkles,
  Activity,
  ReceiptText,
  PiggyBank,
  Target,
  ScrollText,
  Coins,
  CircleDollarSign,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import {
  capitalize,
  riskSeverityLabels,
  riskSeverityTones,
  recommendationPriorityLabels,
  recommendationPriorityTones,
} from "../lib/labels";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type {
  AsyncTaskStatus,
  AsyncTaskSubmitResponse,
  ControllerAction,
  FinancialControllerReport,
  FinancialRecommendation,
  RiskSignal,
} from "../lib/types";
import { formatCurrency, formatNumber, formatPercent } from "../lib/format";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 30;

const textareaClass =
  "w-full resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 hover:border-border-strong focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50";

const SUGGESTED_INTENTS = [
  "Review my overall financial health",
  "Find unusual spending and explain the risks",
  "How should I reduce my expenses?",
  "Review my financial goals and recommend actions",
];

type RunState =
  | { phase: "idle" }
  | { phase: "submitting" }
  | { phase: "polling"; taskId: string }
  | { phase: "success"; report: FinancialControllerReport }
  | { phase: "failure"; message: string };

type BadgeTone = ComponentProps<typeof Badge>["tone"];

const ACTION_TONES: Record<ControllerAction["severity"], BadgeTone> = {
  info: "neutral",
  low: "neutral",
  medium: "warning",
  high: "danger",
};

function toNumberSafely(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

type SpendingCategory = { category?: string; amount?: string };
type BudgetDetails = {
  category_name?: string;
  name?: string;
  amount?: string;
  period?: string;
  spent?: string;
  remaining?: string;
  progress_percent?: string;
};
type GoalDetails = {
  name?: string;
  status?: string;
  target_amount?: string;
  current_amount?: string;
  progress_percent?: string;
  target_date?: string | null;
};

export default function AiControllerPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [intent, setIntent] = useState("");
  const [runState, setRunState] = useState<RunState>({ phase: "idle" });
  const busyRef = useRef(false);

  const report = runState.phase === "success" ? runState.report : null;
  const busy = runState.phase === "submitting" || runState.phase === "polling";
  const pollingTaskId = runState.phase === "polling" ? runState.taskId : null;

  const submit = useCallback(async () => {
    const trimmed = intent.trim();
    if (!trimmed || !user || busyRef.current) return;
    busyRef.current = true;
    setRunState({ phase: "submitting" });
    try {
      const res = await api.post<AsyncTaskSubmitResponse>(
        `/users/${user.id}/ai-controller/async${businessQuery()}`,
        { intent: trimmed }
      );
      busyRef.current = false;
      setRunState({ phase: "polling", taskId: res.task_id });
    } catch (err: unknown) {
      busyRef.current = false;
      const e = err as ApiError;
      setRunState({
        phase: "failure",
        message: e.message || "Unable to submit the controller request. Please try again.",
      });
    }
  }, [intent, user, businessQuery]);

  const reset = useCallback(() => {
    busyRef.current = false;
    setRunState({ phase: "idle" });
    setIntent("");
  }, []);

  useEffect(() => {
    if (!pollingTaskId || !user) return;
    let attempts = 0;
    let disposed = false;

    const poll = async () => {
      attempts += 1;
      try {
        const status = await api.get<AsyncTaskStatus>(
          `/users/${user.id}/ai-controller/async/${pollingTaskId}${businessQuery()}`
        );
        if (disposed) return;

        if (status.status === "SUCCESS") {
          if (status.result && "decision" in status.result) {
            setRunState({ phase: "success", report: status.result });
          } else {
            setRunState({
              phase: "failure",
              message: "The controller completed without a result. Please try again.",
            });
          }
          return;
        }

        if (status.status === "FAILURE") {
          setRunState({
            phase: "failure",
            message: status.message || "The controller run did not complete successfully. Please try again.",
          });
          return;
        }

        if (attempts >= MAX_POLL_ATTEMPTS) {
          setRunState({
            phase: "failure",
            message: "Controller is still processing. Please try again.",
          });
        }
      } catch (err: unknown) {
        if (disposed) return;
        const e = err as ApiError;
        if (e.status) {
          setRunState({
            phase: "failure",
            message:
              e.status === 503
                ? "AI insights are currently unavailable. The AI provider is not configured — contact your administrator."
                : e.status < 500
                  ? e.message || "Unable to check the controller task status."
                  : "The controller run did not complete successfully. Please try again.",
          });
          return;
        }
        if (attempts >= MAX_POLL_ATTEMPTS) {
          setRunState({
            phase: "failure",
            message: "Controller is still processing. Please try again.",
          });
        }
      }
    };

    const id = window.setInterval(poll, POLL_INTERVAL_MS);
    void poll();
    return () => {
      disposed = true;
      window.clearInterval(id);
    };
  }, [pollingTaskId, user, businessQuery]);

  const sourceFacts = report?.source_facts;
  const financialContext = sourceFacts?.extra.financial_context;
  const summary = financialContext?.summary;
  const activity = financialContext?.activity;
  const riskSignals = sourceFacts?.extra.risk_signals ?? [];
  const recommendations = sourceFacts?.extra.recommendations ?? [];
  const citedFacts = sourceFacts?.extra.cited_facts ?? [];
  const spendingByCategory = (financialContext?.spending_by_category ?? []) as SpendingCategory[];
  const budgets = (financialContext?.budgets ?? []) as BudgetDetails[];
  const goals = (financialContext?.financial_goals ?? []) as GoalDetails[];
  const moneyValues = sourceFacts?.money_values ?? null;

  const detailsClass =
    "rounded-lg border border-border bg-surface-raised/30 p-3 open:bg-surface-raised/50";
  const summaryClass =
    "flex cursor-pointer select-none items-center gap-2 text-sm font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/30";

  return (
    <div className="space-y-8">
      <PageHeader
        title="AI Controller"
        description="Send a natural-language instruction and receive an AI-generated financial report and recommendations."
      />

      <Card className="p-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
            <BrainCircuit className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold tracking-tight text-foreground">
              Run the controller
            </h2>
            <p className="text-sm text-muted">
              Describe what you want the controller to do with your finances.
            </p>
          </div>
        </div>

        <div className="mt-4">
          <label htmlFor="controller-intent" className="mb-1.5 block text-sm font-medium text-foreground">
            What would you like the controller to do?
          </label>
          <textarea
            id="controller-intent"
            rows={3}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            disabled={busy}
            placeholder="e.g. Review my spending this month and flag anything unusual."
            className={textareaClass}
            aria-busy={busy}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void submit();
              }
            }}
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {SUGGESTED_INTENTS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={busy}
              onClick={() => {
                setIntent(suggestion);
                busyRef.current = false;
              }}
              className="rounded-full border border-border bg-surface-raised px-3 py-1 text-xs font-medium text-muted transition-colors hover:border-border-strong hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/30 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-faint">
            The controller only proposes actions — it never moves money or
            modifies data on its own.
          </p>
          <div className="flex items-center gap-2">
            {runState.phase === "success" && (
              <Button variant="ghost" size="sm" onClick={reset}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                New instruction
              </Button>
            )}
            <Button
              onClick={() => void submit()}
              disabled={!intent.trim() || busy}
              aria-busy={busy}
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="h-4 w-4" aria-hidden="true" />
              )}
              {runState.phase === "submitting"
                ? "Submitting…"
                : runState.phase === "polling"
                  ? "Running…"
                  : runState.phase === "success"
                    ? "Run again"
                    : "Run controller"}
            </Button>
          </div>
        </div>
      </Card>

      <Card className="p-5" aria-live="polite">
        <div className="flex items-center gap-2.5">
          <Workflow className="h-5 w-5 text-accent-400" aria-hidden="true" />
          <h2 className="text-base font-semibold tracking-tight text-foreground">
            Controller result
          </h2>
        </div>

        {runState.phase === "idle" && (
          <p className="mt-4 rounded-lg border border-dashed border-border-strong bg-surface-raised/30 p-4 text-sm text-muted">
            Run the controller to generate an AI finance report grounded in
            your real accounts, transactions, budgets and goals.
          </p>
        )}

        {runState.phase === "submitting" && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-surface-raised/40 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">Submitting controller request</p>
              <p className="text-xs text-muted">Sending your instruction to the controller…</p>
            </div>
          </div>
        )}

        {runState.phase === "polling" && (
          <div className="mt-4 rounded-lg border border-border bg-surface-raised/40 p-4" aria-busy="true">
            <div className="flex items-center gap-2">
              <Badge tone="accent">RUNNING</Badge>
              <span className="text-xs text-muted">
                Task {runState.taskId.slice(0, 8)}…
              </span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-accent-400" aria-hidden="true" />
              <p className="text-sm text-muted">
                Running controller… this can take a few moments.
              </p>
            </div>
          </div>
        )}

        {runState.phase === "failure" && (
          <div
            className="mt-4 rounded-lg border border-danger-500/25 bg-danger-500/5 p-4"
            id="controller-error"
          >
            <div className="flex items-center gap-2">
              <CircleX className="h-5 w-5 text-danger-400" aria-hidden="true" />
              <Badge tone="danger">FAILURE</Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {runState.message}
            </p>
            <div className="mt-3 flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void submit()}
                disabled={runState.phase !== "failure" || !intent.trim()}
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Retry
              </Button>
              <Button variant="ghost" size="sm" onClick={reset}>
                New instruction
              </Button>
            </div>
          </div>
        )}

        {report && (
          <div className="mt-4 space-y-6">
            <div className="rounded-lg border border-success-500/25 bg-success-500/5 p-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-success-500" aria-hidden="true" />
                <Badge tone="success">SUCCESS</Badge>
                <Badge tone="accent">
                  <Sparkles className="h-3 w-3" aria-hidden="true" />
                  AI-generated
                </Badge>
              </div>
              <p className="mt-2 text-sm text-muted">
                Intent: <span className="text-foreground">{report.intent}</span>
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <SectionHeading
                  id="controller-decision-heading"
                  title="Decision"
                  description="What the controller concluded from your deterministic financial data."
                />
                <p className="mt-3 text-sm leading-relaxed text-muted">
                  {report.decision}
                </p>
              </div>
              <div>
                <SectionHeading
                  id="controller-confidence-heading"
                  title="Confidence"
                  description="How sure the controller is about this decision (0–100%)."
                />
                <div className="mt-3">
                  <StatCard
                    label="Confidence"
                    value={formatPercent(report.confidence * 100, 0)}
                    hint="AI-estimated confidence in the presented decision."
                  />
                </div>
              </div>
            </div>

            <div>
              <SectionHeading
                id="controller-rationale-heading"
                title="Rationale"
                description="The reasoning behind the decision, derived from the run's source facts."
              />
              <p className="mt-3 text-sm leading-relaxed text-muted">
                {report.rationale}
              </p>
            </div>

            <div>
              <SectionHeading
                id="controller-actions-heading"
                title="Proposed actions"
                description="Suggested next steps for you to review. The controller never executes these automatically."
              />
              <div className="mt-3 space-y-3">
                {report.actions.length === 0 && (
                  <p className="rounded-lg border border-dashed border-border-strong bg-surface-raised/30 p-4 text-sm text-muted">
                    No proposed actions were returned for this request.
                  </p>
                )}
                {report.actions.map((action, index) => (
                  <div
                    key={`${action.action_type}-${index}`}
                    className="flex flex-col gap-2 rounded-lg border border-border bg-surface-raised/40 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-medium text-foreground">
                        {action.action_type}
                      </p>
                      <Badge tone={ACTION_TONES[action.severity]}>
                        {capitalize(action.severity)}
                      </Badge>
                    </div>
                    <p className="text-sm leading-relaxed text-muted">
                      {action.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <SectionHeading
                id="controller-source-facts-heading"
                title="Source facts"
                description="The deterministic financial data this run was grounded on. Click a section to expand it."
              />
              <div className="mt-3 space-y-3">
                {moneyValues && (
                  <details className={detailsClass}>
                    <summary className={summaryClass}>
                      <CircleDollarSign className="h-4 w-4 text-accent-400" aria-hidden="true" />
                      Financial Summary
                    </summary>
                    <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <StatCard label="Total income" value={formatCurrency(summary?.total_income)} />
                      <StatCard label="Total expenses" value={formatCurrency(summary?.total_expenses)} />
                      <StatCard label="Net cash flow" value={formatCurrency(summary?.net_cash_flow)} />
                      <StatCard label="Account balance" value={formatCurrency(summary?.account_balance)} />
                    </div>
                  </details>
                )}

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <Activity className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Activity
                  </summary>
                  <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <StatCard label="Transactions" value={formatNumber(activity?.transaction_count, 0)} />
                    <StatCard label="Income transactions" value={formatNumber(activity?.income_transaction_count, 0)} />
                    <StatCard label="Expense transactions" value={formatNumber(activity?.expense_transaction_count, 0)} />
                  </div>
                </details>

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <Coins className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Grounded money values
                  </summary>
                  <div className="mt-3 space-y-2">
                    {Object.entries(moneyValues ?? {}).length === 0 && (
                      <p className="text-xs text-muted">No money values were returned.</p>
                    )}
                    {Object.entries(moneyValues ?? {}).map(([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between gap-2 border-b border-border pb-1.5 text-sm last:border-0 last:pb-0"
                      >
                        <span className="text-muted">{key}</span>
                        <span className="font-medium text-foreground">{value}</span>
                      </div>
                    ))}
                  </div>
                </details>

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <ReceiptText className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Spending by category
                  </summary>
                  <div className="mt-3 space-y-2">
                    {spendingByCategory.length === 0 && (
                      <p className="text-xs text-muted">
                        No spending by category was returned.
                      </p>
                    )}
                    {spendingByCategory.map((category, index) => {
                      const amount = toNumberSafely(category.amount);
                      return (
                        <div
                          key={`${category.category ?? "category"}-${index}`}
                          className="flex items-center justify-between gap-2 border-b border-border pb-1.5 text-sm last:border-0 last:pb-0"
                        >
                          <span className="text-muted">
                            {category.category ? capitalize(category.category) : "Uncategorized"}
                          </span>
                          <span className="font-medium text-foreground">
                            {amount !== null ? formatCurrency(amount) : category.amount ?? "—"}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </details>

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <PiggyBank className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Budgets
                  </summary>
                  <div className="mt-3 space-y-2">
                    {budgets.length === 0 && (
                      <p className="text-xs text-muted">No budgets were returned.</p>
                    )}
                    {budgets.map((budget, index) => {
                      const amount = toNumberSafely(budget.amount);
                      return (
                        <div
                          key={`${budget.category_name ?? budget.name ?? "budget"}-${index}`}
                          className="flex items-center justify-between gap-2 border-b border-border pb-1.5 text-sm last:border-0 last:pb-0"
                        >
                          <span className="text-muted">
                            {budget.category_name ?? budget.name ?? "Budget"}
                            {budget.period ? ` · ${budget.period}` : ""}
                          </span>
                          <span className="font-medium text-foreground">
                            {amount !== null ? formatCurrency(amount) : budget.amount ?? "—"}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </details>

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <Target className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Financial goals
                  </summary>
                  <div className="mt-3 space-y-3">
                    {goals.length === 0 && (
                      <p className="text-xs text-muted">No financial goals were returned.</p>
                    )}
                    {goals.map((goal, index) => {
                      const target = toNumberSafely(goal.target_amount);
                      const current = toNumberSafely(goal.current_amount);
                      const progress = toNumberSafely(goal.progress_percent);
                      return (
                        <div
                          key={`${goal.name ?? "goal"}-${index}`}
                          className="flex flex-col gap-1 border-b border-border pb-2.5 last:border-0 last:pb-0"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-medium text-foreground">
                              {goal.name ?? "Goal"}
                            </span>
                            {goal.status && (
                              <Badge tone="neutral">{capitalize(goal.status)}</Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted">
                            {current !== null ? formatCurrency(current) : "—"}
                            {target !== null ? ` / ${formatCurrency(target)}` : ""}
                            {goal.target_date ? ` · by ${goal.target_date}` : ""}
                          </p>
                          {progress !== null && (
                            <p className="text-xs text-muted-faint">
                              {formatPercent(progress)} complete
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </details>

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <ShieldAlert className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Risk signals
                  </summary>
                  <div className="mt-3">
                    {riskSignals.length === 0 && (
                      <p className="text-xs text-muted">
                        No risk signals were returned for this request.
                      </p>
                    )}
                    <ul className="space-y-3">
                      {riskSignals.map((signal, index) => (
                        <SignalBlock key={`${signal.type}-${index}`} signal={signal} />
                      ))}
                    </ul>
                  </div>
                </details>

                <details className={detailsClass}>
                  <summary className={summaryClass}>
                    <ThumbsUp className="h-4 w-4 text-accent-400" aria-hidden="true" />
                    Recommendations
                  </summary>
                  <div className="mt-3">
                    {recommendations.length === 0 && (
                      <p className="text-xs text-muted">
                        No recommendations were returned for this request.
                      </p>
                    )}
                    <ul className="space-y-3">
                      {recommendations.map((recommendation, index) => (
                        <RecommendationBlock
                          key={`${recommendation.type}-${index}`}
                          recommendation={recommendation}
                        />
                      ))}
                    </ul>
                  </div>
                </details>

                {citedFacts.length > 0 && (
                  <details className={detailsClass}>
                    <summary className={summaryClass}>
                      <ScrollText className="h-4 w-4 text-accent-400" aria-hidden="true" />
                      Cited facts
                    </summary>
                    <div className="mt-3 space-y-2">
                      {citedFacts.map((fact, index) => (
                        <p
                          key={`${fact}-${index}`}
                          className="flex items-start gap-2 text-sm leading-relaxed text-muted"
                        >
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-400" aria-hidden="true" />
                          {fact}
                        </p>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

function SignalBlock({ signal }: { signal: RiskSignal }) {
  const amount = toNumberSafely(signal.amount);
  return (
    <li className="flex flex-col gap-1.5 border-b border-border pb-3 last:border-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{signal.summary}</span>
        <Badge tone={riskSeverityTones[signal.severity]}>
          {riskSeverityLabels[signal.severity]}
        </Badge>
      </div>
      {signal.reason && <p className="text-xs leading-relaxed text-muted">{signal.reason}</p>}
      <p className="text-xs text-muted-faint">
        <span className="rounded-full border border-border bg-surface-raised px-2 py-0.5">
          {capitalize(signal.type)}
        </span>
        {amount !== null && (
          <span className="ml-1.5">· {formatCurrency(amount)}</span>
        )}
        <span className="ml-1.5">· {formatNumber(signal.transaction_ids.length, 0)} transaction(s)</span>
        {signal.explainable === true && (
          <span className="ml-1.5">· AI-explainable</span>
        )}
      </p>
    </li>
  );
}

function RecommendationBlock({ recommendation }: { recommendation: FinancialRecommendation }) {
  const amount = toNumberSafely(recommendation.grounded_amount);
  return (
    <li className="flex flex-col gap-1.5 border-b border-border pb-3 last:border-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{recommendation.title}</span>
        <Badge tone={recommendationPriorityTones[recommendation.priority]}>
          {recommendationPriorityLabels[recommendation.priority]}
        </Badge>
      </div>
      <p className="text-xs leading-relaxed text-muted">{recommendation.body}</p>
      <p className="text-xs text-muted-faint">
        <span className="rounded-full border border-border bg-surface-raised px-2 py-0.5">
          {capitalize(recommendation.type)}
        </span>
        {amount !== null && (
          <span className="ml-1.5">· {formatCurrency(amount)}</span>
        )}
        {recommendation.metric && (
          <span className="ml-1.5">
            · {recommendation.metric.name}: {recommendation.metric.value}
            {recommendation.metric.threshold !== null &&
              recommendation.metric.threshold !== undefined &&
              ` (target ${recommendation.metric.threshold})`}
          </span>
        )}
      </p>
    </li>
  );
}