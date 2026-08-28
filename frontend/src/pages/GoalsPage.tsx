import { useState } from "react";
import { Target, Plus, CalendarDays } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { goalStatusLabels } from "../lib/labels";

export default function GoalsPage() {
  const [showAddNote, setShowAddNote] = useState(false);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Goals"
        description="Track progress toward your savings and financial goals."
        actions={
          <Button onClick={() => setShowAddNote((v) => !v)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Create Goal
          </Button>
        }
      />

      {showAddNote && (
        <Card className="border-accent-500/25 bg-accent-500/5 p-4">
          <p className="text-sm text-foreground">
            Creating a goal requires an authenticated session, planned for a
            later milestone. No changes were submitted.
          </p>
        </Card>
      )}

      <section aria-labelledby="goals-summary">
        <StatCard
          label="Active Goals"
          icon={Target}
          value={<span className="text-muted">Unavailable</span>}
          hint="Goals you are currently working toward"
        />
      </section>

      <section aria-labelledby="goals-list">
        <SectionHeading
          title="Your Goals"
          description="Each goal shows its target and current amount, target date, status, and progress."
        />

        <Card className="mt-4 p-5">
          <EmptyState
            icon={Target}
            title="No goals yet"
            description="When you create a goal, it will appear here with its target and current amount, target date, status badge, and a progress visualization."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowAddNote((v) => !v)}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                Create your first goal
              </Button>
            }
          />
        </Card>
      </section>

      <section aria-labelledby="goal-statuses">
        <SectionHeading
          title="Goal Statuses"
          description="Goals are labeled by their current lifecycle status."
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.keys(goalStatusLabels) as Array<keyof typeof goalStatusLabels>).map(
            (status) => (
              <Badge key={status} tone="neutral">
                <CalendarDays className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                {goalStatusLabels[status]}
              </Badge>
            )
          )}
        </div>
      </section>
    </div>
  );
}
