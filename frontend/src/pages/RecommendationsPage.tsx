import { ThumbsUp, ListChecks, RefreshCw, Lightbulb } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

const PRIORITY_TONES = [
  { label: "High", tone: "danger" as const },
  { label: "Medium", tone: "warning" as const },
  { label: "Low", tone: "success" as const },
];

export default function RecommendationsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Recommendations"
        description="Actionable suggestions generated to improve your financial position."
        actions={
          <Button variant="secondary">
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <section aria-labelledby="recommendations-summary">
        <StatCard
          label="Pending Recommendations"
          icon={ListChecks}
          value={<span className="text-muted">Unavailable</span>}
          hint="Suggestions awaiting action"
        />
      </section>

      <section aria-labelledby="recommendations-list">
        <SectionHeading
          title="Recommendations"
          description="Each suggestion explains a rationale and an action you can take."
        />

        <Card className="mt-4 p-5">
          <EmptyState
            icon={ThumbsUp}
            title="No recommendations yet"
            description="Once your finances are analyzed, actionable suggestions will appear here, each with a priority badge, explanation, and an action."
          />
        </Card>
      </section>

      <section aria-labelledby="priority-legend">
        <SectionHeading
          title="Priority Levels"
          description="How each recommendation is prioritized."
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {PRIORITY_TONES.map((p) => (
            <Card key={p.label} className="flex items-center justify-between p-4">
              <span className="text-sm font-medium text-foreground">
                {p.label}
              </span>
              <Badge tone={p.tone}>{p.label} priority</Badge>
            </Card>
          ))}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
          <Lightbulb className="h-3.5 w-3.5" aria-hidden="true" />
          Recommendations load from the recommendation service; load failures
          are surfaced in place of the list.
        </p>
      </section>
    </div>
  );
}
