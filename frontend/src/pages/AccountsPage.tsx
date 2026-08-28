import { useState } from "react";
import { Wallet, Plus, Landmark, CircleDollarSign } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { accountTypeLabels } from "../lib/labels";

function AccountTypeBadge({ type }: { type: keyof typeof accountTypeLabels }) {
  return <Badge tone="neutral">{accountTypeLabels[type]}</Badge>;
}

export default function AccountsPage() {
  const [showAddNote, setShowAddNote] = useState(false);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Accounts"
        description="All your linked accounts and their running balances at a glance."
        actions={
          <Button onClick={() => setShowAddNote((v) => !v)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Account
          </Button>
        }
      />

      {showAddNote && (
        <Card className="border-accent-500/25 bg-accent-500/5 p-4">
          <p className="text-sm text-foreground">
            Account setup requires an authenticated session, which is planned
            for a later milestone. No changes were submitted.
          </p>
        </Card>
      )}

      <section aria-labelledby="accounts-summary">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label="Total Accounts"
            icon={Landmark}
            value={<span className="text-muted">Unavailable</span>}
            hint="Number of linked accounts"
          />
          <StatCard
            label="Total Balance"
            icon={CircleDollarSign}
            value={<span className="text-muted">Unavailable</span>}
            hint="Sum across all linked accounts"
          />
        </div>
      </section>

      <section aria-labelledby="accounts-list">
        <SectionHeading
          title="Your Accounts"
          description="Linked accounts with their account type and running balance."
        />

        <Card className="mt-4 overflow-hidden p-0">
          <div className="hidden grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border px-5 py-3 sm:grid">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              Account
            </span>
            <span className="w-32 text-right text-xs font-medium uppercase tracking-wide text-muted">
              Type
            </span>
            <span className="w-32 text-right text-xs font-medium uppercase tracking-wide text-muted">
              Balance
            </span>
          </div>
          <div className="p-5">
            <EmptyState
              icon={Wallet}
              title="No accounts linked yet"
              description="When you connect an account, it will appear here with its type and running balance. Links are planned once authentication and the accounts API are available."
              action={
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowAddNote((v) => !v)}
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Add your first account
                </Button>
              }
            />
          </div>
        </Card>
      </section>

      <section aria-labelledby="account-types">
        <SectionHeading
          title="Account Types"
          description="Accounts are grouped by the type of financial instrument they represent."
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.keys(accountTypeLabels) as Array<keyof typeof accountTypeLabels>).map(
            (type) => (
              <AccountTypeBadge key={type} type={type} />
            )
          )}
        </div>
      </section>
    </div>
  );
}
