import { ArrowLeftRight, Search, Download } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { transactionTypeLabels } from "../lib/labels";

export default function TransactionsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Transactions"
        description="Search, filter, and review your income and expenses in one place."
        actions={
          <Button variant="secondary">
            <Download className="h-4 w-4" aria-hidden="true" />
            Export
          </Button>
        }
      />

      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="relative w-full max-w-sm">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-faint"
              aria-hidden="true"
            />
            <Input
              aria-label="Search transactions"
              placeholder="Search by description or amount"
              className="pl-9"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" size="sm">
              All
            </Button>
            {(Object.keys(transactionTypeLabels) as Array<
              keyof typeof transactionTypeLabels
            >).map((type) => (
              <Badge key={type} tone="neutral" className="px-3 py-1">
                {transactionTypeLabels[type]}
              </Badge>
            ))}
          </div>
        </div>
      </Card>

      <section aria-labelledby="transactions-list">
        <SectionHeading
          title="All Transactions"
          description="A chronological view of your income, expenses, and transfers."
        />

        <Card className="mt-4 overflow-hidden p-0">
          <div className="hidden grid-cols-[1fr_auto_auto_auto] items-center gap-4 border-b border-border px-5 py-3 md:grid">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              Description
            </span>
            <span className="w-24 text-right text-xs font-medium uppercase tracking-wide text-muted">
              Date
            </span>
            <span className="w-24 text-right text-xs font-medium uppercase tracking-wide text-muted">
              Type
            </span>
            <span className="w-28 text-right text-xs font-medium uppercase tracking-wide text-muted">
              Amount
            </span>
          </div>
          <div className="p-5">
            <EmptyState
              icon={ArrowLeftRight}
              title="No transactions to display"
              description="Once transactions are recorded, they'll appear here with their type, date, and amount. You can open any transaction to view or manage its details at /transactions/:id."
            />
          </div>
        </Card>
      </section>
    </div>
  );
}
