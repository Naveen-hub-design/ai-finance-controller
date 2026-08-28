import { useState } from "react";
import { PiggyBank, Plus, CalendarRange, Gauge } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { budgetPeriodLabels } from "../lib/labels";

export default function BudgetsPage() {
  const [showAddNote, setShowAddNote] = useState(false);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Budgets"
        description="Set and monitor budgets across your spending categories."
        actions={
          <Button onClick={() => setShowAddNote((v) => !v)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Create Budget
          </Button>
        }
      />

      {showAddNote && (
        <Card className="border-accent-500/25 bg-accent-500/5 p-4">
          <p className="text-sm text-foreground">
            Creating a budget requires an authenticated session, planned for a
            later milestone. No changes were submitted.
          </p>
        </Card>
      )}

      <section aria-labelledby="budgets-summary">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label="Active Budgets"
            icon={PiggyBank}
            value={<span className="text-muted">Unavailable</span>}
            hint="Budgets currently in effect"
          />
          <StatCard
            label="Allocated"
            icon={Gauge}
            value={<span className="text-muted">Unavailable</span>}
            hint="Total budgeted amount"
          />
        </div>
      </section>

      <section aria-labelledby="budgets-list">
        <SectionHeading
          title="Your Budgets"
          description="Each budget tracks a category, amount, period, and spending progress."
        />

        <Card className="mt-4 p-5">
          <EmptyState
            icon={PiggyBank}
            title="No budgets yet"
            description="When you create a budget, it will appear here with its category, amount, period, and a live progress indicator against your spending."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowAddNote((v) => !v)}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                Create your first budget
              </Button>
            }
          />
        </Card>
      </section>

      <section aria-labelledby="budget-periods">
        <SectionHeading
          title="Budget Periods"
          description="Budgets are evaluated over weekly, monthly, or yearly periods."
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.keys(budgetPeriodLabels) as Array<keyof typeof budgetPeriodLabels>).map(
            (period) => (
              <Badge key={period} tone="neutral">
                <CalendarRange className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                {budgetPeriodLabels[period]}
              </Badge>
            )
          )}
        </div>
        <p className="mt-3 text-xs text-muted-faint">
          Health status badges (on track, near limit, over) will indicate how a
          budget compares to actual spending once data is available.
        </p>
      </section>
    </div>
  );
}
