import { useCallback, useEffect, useRef, useState } from "react";
import {
  ThumbsUp,
  ListChecks,
  RefreshCw,
  Lightbulb,
  Loader2,
  RotateCcw,
  Gauge,
  Info,
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
  recommendationPriorityLabels,
  recommendationPriorityTones,
} from "../lib/labels";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type {
  FinancialRecommendation,
  RecommendationsResponse,
} from "../lib/types";
import { formatCurrency, formatNumber } from "../lib/format";

type LoadState =
  | { status: "loading" }
  | { status: "success"; recommendations: FinancialRecommendation[] }
  | { status: "forbidden" }
  | { status: "error"; message: string };

function priorityIcon(
  priority: FinancialRecommendation["priority"]
): LucideIcon {
  switch (priority) {
    case "high":
      return Lightbulb;
    case "medium":
      return ThumbsUp;
    default:
      return ListChecks;
  }
}

function RecommendationCard({
  recommendation,
}: {
  recommendation: FinancialRecommendation;
}) {
  const Icon = priorityIcon(recommendation.priority);
  const hasMetric =
    recommendation.metric &&
    typeof recommendation.metric === "object" &&
    "name" in recommendation.metric &&
    "value" in recommendation.metric &&
    "threshold" in recommendation.metric;

  return (
    <Card className="card-interactive flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-medium text-foreground">
              {recommendation.title || "Recommendation"}
            </h3>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-faint">
              <Badge tone="neutral">{recommendation.type}</Badge>
            </p>
          </div>
        </div>
        <Badge tone={recommendationPriorityTones[recommendation.priority]}>
          {recommendationPriorityLabels[recommendation.priority]} priority
        </Badge>
      </div>

      {recommendation.body && (
        <p className="text-sm leading-relaxed text-muted">
          {recommendation.body}
        </p>
      )}

      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-faint">
        {recommendation.grounded_amount && (
          <span className="flex items-center gap-1.5">
            <span className="font-medium text-foreground">
              {formatCurrency(recommendation.grounded_amount)}
            </span>
            grounded amount
          </span>
        )}
        {hasMetric && (
          <span className="flex items-center gap-1.5">
            <Gauge className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="text-muted">
              {recommendation.metric.name}:{" "}
              <span className="font-medium text-foreground">
                {recommendation.metric.value}
              </span>
              <span className="text-muted-faint">
                {" "}
                (target {recommendation.metric.threshold})
              </span>
            </span>
          </span>
        )}
      </div>
    </Card>
  );
}

export default function RecommendationsPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view your recommendations.",
      });
      return;
    }

    cancelledRef.current = false;
    setState({ status: "loading" });

    try {
      const res = await api.get<RecommendationsResponse>(
        `/users/${user.id}/recommendations${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", recommendations: res.recommendations ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      if (e.status === 403) {
        setState({ status: "forbidden" });
        return;
      }
      setState({
        status: "error",
        message: e.message || "Unable to load your recommendations.",
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
      const res = await api.get<RecommendationsResponse>(
        `/users/${user.id}/recommendations${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", recommendations: res.recommendations ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      if (e.status === 403) {
        setState({ status: "forbidden" });
        return;
      }
      setState({
        status: "error",
        message: e.message || "Unable to refresh your recommendations.",
      });
    } finally {
      if (!cancelledRef.current) setRefreshing(false);
    }
  }, [user, businessQuery]);

  const recommendations =
    state.status === "success" ? state.recommendations : [];
  const highCount = recommendations.filter(
    (r) => r.priority === "high"
  ).length;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Recommendations"
        description="What should you do next? Actionable suggestions generated to improve your financial position."
        actions={
          <Button
            variant="secondary"
            onClick={refresh}
            disabled={refreshing || state.status === "loading"}
            title="Refresh recommendations"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </Button>
        }
      />

      <section aria-labelledby="recommendations-overview-heading">
        <SectionHeading
          id="recommendations-overview-heading"
          title="Recommendation Overview"
          description="A summary of the recommendations currently available."
        />
        {state.status === "loading" && (
          <Card className="mt-4 flex items-center gap-3 p-6">
            <Loader2
              className="h-5 w-5 animate-spin text-accent-400"
              aria-hidden="true"
            />
            <p className="text-sm text-muted">Generating recommendations…</p>
          </Card>
        )}

        {state.status === "forbidden" && (
          <div className="mt-4">
            <ForbiddenState />
          </div>
        )}

        {state.status === "error" && (
          <div className="mt-4">
            <EmptyState
              icon={ThumbsUp}
              title="Could not load recommendations"
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
              label="Recommendations"
              icon={ListChecks}
              value={formatNumber(recommendations.length)}
              hint="Actionable suggestions generated for your finances"
            />
            <StatCard
              label="High Priority"
              icon={Lightbulb}
              value={formatNumber(highCount)}
              hint="Recommendations to address first"
              iconClassName="text-danger-400"
            />
          </div>
        )}
      </section>

      <section aria-labelledby="recommendations-list-heading">
        <SectionHeading
          id="recommendations-list-heading"
          title="Recommendations"
          description="Each suggestion explains the underlying rule and the reason it matters."
        />

        {state.status === "error" && (
          <div className="mt-4">
            <EmptyState
              icon={ThumbsUp}
              title="Recommendations unavailable"
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

        {state.status === "success" && recommendations.length === 0 && (
          <Card className="mt-4">
            <EmptyState
              icon={ThumbsUp}
              title="No recommendations yet"
              description="Once your finances are analyzed, actionable suggestions will appear here, each with a priority badge and an explanation."
            />
          </Card>
        )}

        {state.status === "success" && recommendations.length > 0 && (
          <div
            aria-live="polite"
            className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
          >
            {recommendations.map((rec, index) => (
              <RecommendationCard
                key={`${rec.type}-${rec.title}-${index}`}
                recommendation={rec}
              />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="priority-legend-heading">
        <SectionHeading
          id="priority-legend-heading"
          title="Priority Levels"
          description="How each recommendation is prioritized."
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {(["high", "medium", "low"] as const).map((priority) => {
            const Icon = priorityIcon(priority);
            return (
              <Card key={priority} className="card-interactive flex flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <Badge tone={recommendationPriorityTones[priority]}>
                    {recommendationPriorityLabels[priority]} priority
                  </Badge>
                </div>
                <p className="text-sm text-muted">
                  {priority === "high"
                    ? "Address as soon as possible."
                    : priority === "medium"
                      ? "Consider in the near term."
                      : "Optional, informational."}
                </p>
              </Card>
            );
          })}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
          <Info className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          Recommendations are generated from deterministic financial rules and
          grounding facts.
        </p>
      </section>
    </div>
  );
}