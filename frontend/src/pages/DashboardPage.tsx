import type { ComponentProps } from "react";
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
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

function MetricCard({
  label,
  icon,
  hint,
}: {
  label: string;
  icon: ComponentProps<typeof StatCard>["icon"];
  hint: string;
}) {
  return (
    <StatCard
      label={label}
      icon={icon}
      value={<span className="text-muted">Unavailable</span>}
      hint={hint}
    />
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="A high-level view of your financial health, upcoming obligations, and key metrics."
      />

      <section aria-labelledby="dashboard-metrics">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Total Balance"
            icon={Wallet}
            hint="Sum of all account balances"
          />
          <MetricCard
            label="Income"
            icon={TrendingUp}
            hint="Total income this period"
          />
          <MetricCard
            label="Expenses"
            icon={TrendingDown}
            hint="Total expenses this period"
          />
          <MetricCard
            label="Net Cash Flow"
            icon={Activity}
            hint="Income minus expenses"
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="space-y-6">
            <section aria-labelledby="overview-heading">
              <SectionHeading
                title="Financial Overview"
                description="Trends across income, expenses, and balance over time."
              />
              <div className="mt-4">
                <EmptyState
                  icon={Activity}
                  title="Trend data unavailable"
                  description="Once accounts are connected and transactions are recorded, income and expense trends will appear here."
                />
              </div>
            </section>

            <section aria-labelledby="recent-activity-heading">
              <SectionHeading
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
                <EmptyState
                  icon={Clock}
                  title="No recent activity"
                  description="Transactions you record will show up here as the latest activity."
                />
              </div>
            </section>
          </div>
        </div>

        <aside className="space-y-6" aria-label="AI and financial insights">
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                <Landmark className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm text-muted">Accounts</p>
                <p className="text-sm font-medium text-foreground">
                  No accounts linked
                </p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted">
              Link your accounts to start tracking balances and transactions.
            </p>
            <Link to="/accounts" className="mt-4 block">
              <Button variant="secondary" size="sm" className="w-full">
                Manage accounts
              </Button>
            </Link>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                <Sparkles className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm text-muted">AI Controller</p>
                <Badge tone="neutral" className="mt-1">
                  No report yet
                </Badge>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted">
              Ask the AI controller for a report on your finances.
            </p>
            <Link to="/ai-controller" className="mt-4 block">
              <Button variant="primary" size="sm" className="w-full">
                <Sparkles className="h-4 w-4" aria-hidden="true" />
                Ask the controller
              </Button>
            </Link>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-danger-400">
                <ShieldAlert className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm text-muted">Risks</p>
                <Badge tone="neutral" className="mt-1">
                  No flags
                </Badge>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted">
              Anomalies and risk signals will be surfaced here.
            </p>
            <Link to="/risks" className="mt-4 block">
              <Button variant="ghost" size="sm" className="w-full">
                Review risks
              </Button>
            </Link>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-success-500">
                <ThumbsUp className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm text-muted">Recommendations</p>
                <Badge tone="neutral" className="mt-1">
                  None yet
                </Badge>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted">
              Actionable suggestions to improve your finances will appear here.
            </p>
            <Link to="/recommendations" className="mt-4 block">
              <Button variant="ghost" size="sm" className="w-full">
                View recommendations
              </Button>
            </Link>
          </Card>
        </aside>
      </section>
    </div>
  );
}
