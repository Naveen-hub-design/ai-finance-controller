import { useCallback, useEffect, useRef, useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  AlertTriangle,
  RefreshCw,
  Loader2,
  RotateCcw,
  FileQuestion,
  Hash,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { ForbiddenState } from "../components/ui/ForbiddenState";
import {
  riskSeverityLabels,
  riskSeverityTones,
} from "../lib/labels";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type { RiskIntelligenceResponse, RiskSignal } from "../lib/types";
import { formatCurrency, formatNumber } from "../lib/format";

type LoadState =
  | { status: "loading" }
  | { status: "success"; signals: RiskSignal[] }
  | { status: "forbidden" }
  | { status: "error"; message: string };

function toNumberSafely(
  value: string | number | null | undefined
): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function riskIcon(severity: RiskSignal["severity"]): LucideIcon {
  switch (severity) {
    case "high":
      return AlertTriangle;
    case "medium":
      return Activity;
    default:
      return ShieldCheck;
  }
}

function RiskSignalCard({ signal }: { signal: RiskSignal }) {
  const Icon = riskIcon(signal.severity);
  const amount = toNumberSafely(signal.amount);
  return (
    <Card className="card-interactive flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-medium text-foreground">
              {signal.summary || "Risk signal"}
            </h3>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-faint">
              <Badge tone="neutral">{signal.type}</Badge>
            </p>
          </div>
        </div>
        <Badge tone={riskSeverityTones[signal.severity]}>
          {riskSeverityLabels[signal.severity]}
        </Badge>
      </div>

      {signal.reason && (
        <p className="text-sm leading-relaxed text-muted">{signal.reason}</p>
      )}

      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-faint">
        {amount !== null && (
          <span className="flex items-center gap-1.5">
            <span className="font-medium text-foreground">
              {formatCurrency(amount)}
            </span>
            affected amount
          </span>
        )}
        {signal.explainable === true && (
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            Explainable rule
          </span>
        )}
        {signal.transaction_ids.length > 0 && (
          <span className="flex items-center gap-1.5">
            <Hash className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {signal.transaction_ids.length.toLocaleString()}{" "}
            transaction{signal.transaction_ids.length === 1 ? "" : "s"}
          </span>
        )}
      </div>
    </Card>
  );
}

export default function RisksPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view your risk intelligence.",
      });
      return;
    }

    cancelledRef.current = false;
    setState({ status: "loading" });

    try {
      const res = await api.get<RiskIntelligenceResponse>(
        `/users/${user.id}/risk-intelligence${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", signals: res.signals ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      if (e.status === 403) {
        setState({ status: "forbidden" });
        return;
      }
      setState({
        status: "error",
        message: e.message || "Unable to load your risk intelligence.",
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
      const res = await api.get<RiskIntelligenceResponse>(
        `/users/${user.id}/risk-intelligence${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", signals: res.signals ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      if (e.status === 403) {
        setState({ status: "forbidden" });
        return;
      }
      setState({
        status: "error",
        message: e.message || "Unable to refresh your risk intelligence.",
      });
    } finally {
      if (!cancelledRef.current) setRefreshing(false);
    }
  }, [user, businessQuery]);

  const signals = state.status === "success" ? state.signals : [];
  const highCount = signals.filter((s) => s.severity === "high").length;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Risks"
        description="Where could your finances be at risk? Anomalies and risk signals surfaced from your financial activity."
        actions={
          <Button
            variant="secondary"
            onClick={refresh}
            disabled={refreshing || state.status === "loading"}
            title="Refresh risk intelligence"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </Button>
        }
      />

      <section aria-labelledby="risk-overview-heading">
        <SectionHeading
          id="risk-overview-heading"
          title="Risk Overview"
          description="A summary of the risk signals currently detected."
        />
        {state.status === "loading" && (
          <Card className="mt-4 flex items-center gap-3 p-6">
            <Loader2
              className="h-5 w-5 animate-spin text-accent-400"
              aria-hidden="true"
            />
            <p className="text-sm text-muted">Analyzing your risk signals…</p>
          </Card>
        )}

        {state.status === "error" && (
          <div className="mt-4">
            <EmptyState
              icon={ShieldAlert}
              title="Could not load risk intelligence"
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
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <StatCard
              label="Total Signals"
              icon={Activity}
              value={formatNumber(signals.length)}
              hint="Anomalies and risk flags detected across your accounts"
            />
            <StatCard
              label="High Severity"
              icon={AlertTriangle}
              value={formatNumber(highCount)}
              hint="Signals flagged as high risk"
              iconClassName="text-danger-400"
            />
          </div>
        )}
      </section>

      <section aria-labelledby="risk-list-heading">
        <SectionHeading
          id="risk-list-heading"
          title="Detected Risks"
          description="Each signal includes a severity, the underlying rule, and the transactions it affects."
        />

        {state.status === "forbidden" && (
          <div className="mt-4">
            <ForbiddenState />
          </div>
        )}

        {state.status === "error" && (
          <div className="mt-4">
            <EmptyState
              icon={ShieldAlert}
              title="Risk intelligence unavailable"
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

        {state.status === "success" && signals.length === 0 && (
          <Card className="mt-4">
            <EmptyState
              icon={ShieldCheck}
              title="No risk signals detected"
              description="No anomalies were found in your recent financial activity. As new transactions are analyzed, risks will appear here."
            />
          </Card>
        )}

        {state.status === "success" && signals.length > 0 && (
          <div
            aria-live="polite"
            className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
          >
            {signals.map((signal, index) => (
              <RiskSignalCard
                key={`${signal.type}-${signal.transaction_ids.join(",") || index}`}
                signal={signal}
              />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="severity-legend-heading">
        <SectionHeading
          id="severity-legend-heading"
          title="Severity Levels"
          description="How individual risk signals are graded by the detection rules."
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {(["high", "medium", "low"] as const).map((severity) => {
            const Icon = riskIcon(severity);
            return (
              <Card key={severity} className="card-interactive flex flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <Badge tone={riskSeverityTones[severity]}>
                    {riskSeverityLabels[severity]}
                  </Badge>
                </div>
                <p className="text-sm text-muted">
                  {severity === "high"
                    ? "Unusually large, high-threshold signals."
                    : severity === "medium"
                      ? "Concentration, duplicates, and frequency signals."
                      : "Low-impact informational signals such as round amounts."}
                </p>
              </Card>
            );
          })}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
          <FileQuestion className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          Risks are deterministic candidate signals, not proof of fraud.
        </p>
      </section>
    </div>
  );
}