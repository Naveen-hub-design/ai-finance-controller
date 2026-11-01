import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ComponentProps,
} from "react";
import {
  RefreshCw,
  Loader2,
  GitCompareArrows,
  CircleX,
  CheckCircle2,
  CircleDollarSign,
  ReceiptText,
  Scale,
  Sparkles,
  Clock,
  Gauge,
  AlertTriangle,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type {
  AsyncTaskStatus,
  AsyncTaskSubmitResponse,
  ReconciliationReport,
  ReconciliationLineReview,
  ReconciliationExplainResponse,
} from "../lib/types";
import {
  formatCurrency,
  formatShortDate,
  formatPercent,
  formatNumber,
} from "../lib/format";

const SOURCE = "bank_statement";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 30;

type BadgeTone = ComponentProps<typeof Badge>["tone"];

type RunState =
  | { phase: "idle" }
  | { phase: "running" }
  | { phase: "submitting" }
  | { phase: "polling"; taskId: string }
  | { phase: "success"; report: ReconciliationReport }
  | { phase: "failure"; message: string };

const CATEGORY_META: Record<
  string,
  { label: string; tone: BadgeTone }
> = {
  MISSING_LEDGER_RECORD: { label: "Missing ledger record", tone: "danger" },
  AMOUNT_MISMATCH: { label: "Amount mismatch", tone: "warning" },
  DATE_MISMATCH: { label: "Date mismatch", tone: "warning" },
  DUPLICATE_RECORD: { label: "Duplicate record", tone: "warning" },
  INVALID_RECORD: { label: "Invalid record", tone: "danger" },
  OTHER: { label: "Other", tone: "neutral" },
};

const REVIEW_TONES: Record<string, BadgeTone> = {
  UNRESOLVED: "danger",
  REVIEWED: "warning",
  RESOLVED: "success",
};

function moneyToNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const normalized = value.trim();
  const payload = normalized.endsWith("%") ? normalized.slice(0, -1) : normalized;
  const parsed = Number(payload);
  return Number.isFinite(parsed) ? parsed : null;
}

function categoryTone(category: string): BadgeTone {
  return CATEGORY_META[category]?.tone ?? "neutral";
}

function categoryLabel(category: string): string {
  return CATEGORY_META[category]?.label ?? category;
}

function matchRateTone(rate: number | null): BadgeTone {
  if (rate === null) return "neutral";
  if (rate >= 80) return "success";
  if (rate >= 50) return "warning";
  return "danger";
}

export default function ReconciliationPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [runState, setRunState] = useState<RunState>({ phase: "idle" });
  const busyRef = useRef(false);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
  const [explaining, setExplaining] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<
    ReconciliationExplainResponse | null
  >(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);

  const report = runState.phase === "success" ? runState.report : null;
  const busy = runState.phase === "running" || runState.phase === "submitting" || runState.phase === "polling";
  const pollingTaskId = runState.phase === "polling" ? runState.taskId : null;

  const run = useCallback(async () => {
    if (!user || busyRef.current) return;
    busyRef.current = true;
    setRunState({ phase: "running" });
    setExplanation(null);
    setExplanationError(null);
    try {
      const res = await api.post<ReconciliationReport>(
        `/users/${user.id}/reconcile${businessQuery()}`,
        { source: SOURCE }
      );
      setRunState({ phase: "success", report: res });
    } catch (err: unknown) {
      const e = err as ApiError;
      setRunState({
        phase: "failure",
        message: e.message || "Unable to run reconciliation. Please try again.",
      });
    } finally {
      busyRef.current = false;
    }
  }, [user, businessQuery]);

  const runAsync = useCallback(async () => {
    if (!user || busyRef.current) return;
    busyRef.current = true;
    setRunState({ phase: "submitting" });
    setExplanation(null);
    setExplanationError(null);
    try {
      const res = await api.post<AsyncTaskSubmitResponse>(
        `/users/${user.id}/reconcile/async${businessQuery()}`,
        { source: SOURCE }
      );
      busyRef.current = false;
      setRunState({ phase: "polling", taskId: res.task_id });
    } catch (err: unknown) {
      busyRef.current = false;
      const e = err as ApiError;
      setRunState({
        phase: "failure",
        message:
          e.message ||
          "Unable to dispatch reconciliation to the worker. Please try again.",
      });
    }
  }, [user, businessQuery]);

  useEffect(() => {
    if (!pollingTaskId || !user) return;
    let attempts = 0;
    let disposed = false;

    const poll = async () => {
      attempts += 1;
      try {
        const status = await api.get<AsyncTaskStatus>(
          `/users/${user.id}/reconcile/async/${pollingTaskId}${businessQuery()}`
        );
        if (disposed) return;

        if (status.status === "SUCCESS") {
          if (status.result && "batch_size" in status.result) {
            setRunState({ phase: "success", report: status.result });
          } else {
            setRunState({
              phase: "failure",
              message:
                "Reconciliation completed without a report. Please try again.",
            });
          }
          return;
        }

        if (status.status === "FAILURE") {
          setRunState({
            phase: "failure",
            message:
              status.message ||
              "The reconciliation did not complete successfully. Please try again.",
          });
          return;
        }

        if (attempts >= MAX_POLL_ATTEMPTS) {
          setRunState({
            phase: "failure",
            message: "Reconciliation is still processing. Please try again.",
          });
        }
      } catch (err: unknown) {
        if (disposed) return;
        const e = err as ApiError;
        if (e.status && e.status < 500) {
          setRunState({
            phase: "failure",
            message:
              e.message || "Unable to check the reconciliation task status.",
          });
          return;
        }
        if (attempts >= MAX_POLL_ATTEMPTS) {
          setRunState({
            phase: "failure",
            message: "Reconciliation is still processing. Please try again.",
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

  const updateReviewStatus = useCallback(
    async (lineId: string, reviewStatus: string) => {
      if (!user || reviewBusy) return;
      setReviewBusy(lineId);
      try {
        const res = await api.patch<ReconciliationLineReview>(
          `/users/${user.id}/reconcile/lines/${lineId}/review`,
          { review_status: reviewStatus }
        );
        if (report) {
          setRunState({
            phase: "success",
            report: {
              ...report,
              exceptions: report.exceptions.map((ex) =>
                ex.statement_line_id === lineId
                  ? { ...ex, review_status: res.review_status }
                  : ex
              ),
            },
          });
        }
      } catch (err: unknown) {
        const e = err as ApiError;
        setExplanationError(
          e.message || "Unable to update review status. Please try again."
        );
      } finally {
        setReviewBusy(null);
      }
    },
    [user, reviewBusy, report]
  );

  const explainException = useCallback(
    async (lineId: string) => {
      if (!user || explaining) return;
      setExplaining(lineId);
      setExplanation(null);
      setExplanationError(null);
      try {
        const res = await api.post<ReconciliationExplainResponse>(
          `/users/${user.id}/reconcile/lines/${lineId}/explain`,
          {}
        );
        setExplanation(res);
      } catch (err: unknown) {
        const e = err as ApiError;
        setExplanationError(
          e.message || "Unable to get an AI explanation. Please try again."
        );
      } finally {
        setExplaining(null);
      }
    },
    [user, explaining]
  );

  const matchRate = moneyToNumber(report?.match_rate);
  const exceptionRate = moneyToNumber(report?.exception_rate);

  const detailsClass =
    "group rounded-lg border border-border bg-surface-raised/30 p-3 open:bg-surface-raised/50";
  const summaryClass =
    "flex cursor-pointer list-none items-center gap-2 text-sm font-medium text-foreground";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reconciliation"
        description="Close a finance-ops loop by matching your external bank statement against your internal ledger, then review the match rate, throughput, and the exceptions that could not be resolved."
      />

      <Card className="p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500/10 text-accent-400">
              <GitCompareArrows className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                Run the reconciliation batch
              </p>
              <p className="mt-1 text-sm text-muted">
                Matches the batch of bank-statement records against the internal ledger and
                reports the match rate, throughput, and unresolved exceptions.
              </p>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button
              onClick={run}
              disabled={busy}
              title="Run reconciliation synchronously and wait for the result"
            >
              {runState.phase === "running" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              {runState.phase === "running"
                ? "Reconciling…"
                : runState.phase === "success"
                  ? "Re-run"
                  : "Run reconciliation"}
            </Button>
            <Button
              variant="secondary"
              onClick={runAsync}
              disabled={busy}
              title="Dispatch the batch to the background worker and poll for the report"
            >
              {runState.phase === "polling" || runState.phase === "submitting" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Gauge className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              {runState.phase === "polling"
                ? "Processing…"
                : "Run async (worker)"}
            </Button>
          </div>
        </div>
      </Card>

      {runState.phase === "running" && (
        <Card className="p-6 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-accent-400" aria-hidden="true" />
          <p className="mt-3 text-sm text-muted">Matching statement lines against the internal ledger…</p>
        </Card>
      )}

      {runState.phase === "submitting" && (
        <Card className="p-6 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-accent-400" aria-hidden="true" />
          <p className="mt-3 text-sm text-muted">Dispatching the reconciliation batch to the worker…</p>
        </Card>
      )}

      {runState.phase === "polling" && (
        <Card className="p-6 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-accent-400" aria-hidden="true" />
          <p className="mt-3 text-sm text-muted">Processing financial records in the background…</p>
        </Card>
      )}

      {runState.phase === "failure" && (
        <Card className="border-danger-500/30 p-5">
          <div className="flex items-start gap-3">
            <CircleX className="mt-0.5 h-5 w-5 text-danger-400" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">Reconciliation failed</p>
              <p className="mt-1 text-sm text-muted">{runState.message}</p>
            </div>
          </div>
        </Card>
      )}

      {report && (
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionHeading
              id="reconciliation-summary-heading"
              title="Reconciliation summary"
              description={`Source: ${report.source} · ${formatShortDate(report.created_at)}`}
            />
            <div className="flex flex-wrap gap-2">
              <Badge tone={matchRateTone(matchRate)}>
                {formatPercent(matchRate ?? 0, 2)} matched
              </Badge>
              <Badge tone={report.exceptions.length ? "danger" : "success"}>
                {formatPercent(exceptionRate ?? 0, 2)} exceptions
              </Badge>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Records processed" value={`${report.batch_size}`} />
            <StatCard label="Matched" value={`${report.matched_count}`} />
            <StatCard label="Exceptions" value={`${report.exception_count}`} />
            <StatCard label="Match rate" value={report.match_rate} />
            <StatCard label="Exception rate" value={report.exception_rate} />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard
              label="Processing time"
              value={`${formatNumber(report.processing_duration_seconds, 3)}s`}
              icon={Clock}
            />
            <StatCard
              label="Throughput"
              value={`${formatNumber(report.throughput, 2)} rec/sec`}
              icon={Gauge}
            />
            <StatCard
              label="Ledger matched"
              value={`${report.ledger_matched_count} txn`}
              icon={Scale}
            />
          </div>

          <div className="mt-6 space-y-4">
            <div>
              <SectionHeading
                id="reconciliation-exceptions-heading"
                title={`Unresolved exceptions (${report.exceptions.length})`}
                description="Statement lines with no matching internal ledger entry — the loop could not resolve these. Review each one, optionally get an AI explanation, and mark it reviewed/resolved."
              />
              {explanationError && (
                <p className="mt-3 flex items-start gap-2 rounded-lg border border-danger-500/30 bg-danger-500/5 p-3 text-sm text-danger-400">
                  <CircleX className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  {explanationError}
                </p>
              )}
              {report.exceptions.length === 0 ? (
                <p className="mt-3 rounded-lg border border-dashed border-border-strong bg-surface-raised/30 p-4 text-sm text-muted">
                  No exceptions. All statement lines were reconciled.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {report.exceptions.map((exception, idx) => {
                    const amount = moneyToNumber(exception.statement_amount);
                    return (
                      <div
                        key={exception.statement_line_id}
                        className="flex flex-col gap-2 rounded-lg border border-danger-500/20 bg-danger-500/5 p-4"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-medium text-muted">
                              #{idx + 1}
                            </span>
                            <Badge tone={categoryTone(exception.category)}>
                              {categoryLabel(exception.category)}
                            </Badge>
                            <Badge
                              tone={REVIEW_TONES[exception.review_status] ?? "neutral"}
                            >
                              {exception.review_status}
                            </Badge>
                          </div>
                          <span className="text-sm font-semibold text-danger-400">
                            {amount !== null ? formatCurrency(amount) : exception.statement_amount}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <p className="text-sm font-medium text-foreground">
                            {exception.statement_description}
                          </p>
                          <p className="text-xs text-muted">
                            {formatShortDate(exception.statement_date)}
                          </p>
                        </div>
                        <p className="text-xs text-muted">{exception.reason}</p>

                        <div className="mt-1 flex flex-wrap gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={reviewBusy === exception.statement_line_id}
                            onClick={() =>
                              updateReviewStatus(
                                exception.statement_line_id,
                                "REVIEWED"
                              )
                            }
                          >
                            Mark reviewed
                          </Button>
                          {exception.review_status !== "RESOLVED" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={reviewBusy === exception.statement_line_id}
                              onClick={() =>
                                updateReviewStatus(
                                  exception.statement_line_id,
                                  "RESOLVED"
                                )
                              }
                            >
                              Mark resolved
                            </Button>
                          )}
                          <Button
                            size="sm"
                            disabled={explaining === exception.statement_line_id}
                            onClick={() =>
                              explainException(exception.statement_line_id)
                            }
                          >
                            {explaining === exception.statement_line_id ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                            ) : (
                              <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
                            )}
                            Explain with AI
                          </Button>
                        </div>

                        {explanation?.statement_line_id ===
                          exception.statement_line_id && (
                          <div className="mt-2 rounded-lg border border-accent-500/25 bg-accent-500/5 p-3">
                            <div className="flex items-start gap-2">
                              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" aria-hidden="true" />
                              <div className="space-y-2 text-sm">
                                <p className="font-medium text-foreground">
                                  AI proposal
                                </p>
                                <div className="space-y-2 text-muted">
                                  <p className="whitespace-pre-wrap">
                                    {explanation.explanation}
                                  </p>
                                </div>
                                <p className="text-xs">
                                  Suggested next step (proposal only):{" "}
                                  {explanation.suggested_resolution}
                                </p>
                                <p className="text-xs">
                                  This is an AI suggestion. It never modifies
                                  ledger or statement records — a human action
                                  is required to resolve the exception.
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div>
              <SectionHeading
                id="reconciliation-matched-heading"
                title={`Matched lines (${report.matched.length})`}
                description="Statement lines that were successfully matched to an internal ledger entry. Expand to review the details."
              />
              {report.matched.length === 0 ? (
                <p className="mt-3 rounded-lg border border-dashed border-border-strong bg-surface-raised/30 p-4 text-sm text-muted">
                  No lines were matched.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {report.matched.map((match) => {
                    const amount = moneyToNumber(match.statement_amount);
                    return (
                      <details key={match.statement_line_id} className={detailsClass}>
                        <summary className={summaryClass}>
                          <CheckCircle2 className="h-4 w-4 text-success-400" aria-hidden="true" />
                          {match.statement_description}
                          <span className="ml-auto text-sm font-semibold text-foreground">
                            {amount !== null ? formatCurrency(amount) : match.statement_amount}
                          </span>
                        </summary>
                        <div className="mt-3 space-y-2 text-sm">
                          <div className="flex items-center gap-2 text-muted">
                            <CircleDollarSign className="h-4 w-4 text-accent-400" aria-hidden="true" />
                            Internal transaction matches on {match.match_basis}.
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted">
                            <ReceiptText className="h-4 w-4 text-accent-400" aria-hidden="true" />
                            {formatShortDate(match.statement_date)}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted">
                            <Scale className="h-4 w-4 text-accent-400" aria-hidden="true" />
                            Ledger txn {match.matched_transaction_id}
                          </div>
                        </div>
                      </details>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {runState.phase === "idle" && (
        <Card className="p-6">
          <p className="text-sm text-muted">
            Run the reconciliation to match your statement against the internal ledger and review
            the match rate, throughput, and unresolved exceptions. Use the async option to process
            the batch in the background worker and poll for the report.
          </p>
        </Card>
      )}
    </div>
  );
}