import { useState } from "react";
import { Tags, Plus, TrendingUp, TrendingDown } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

function CategoryGroup({
  title,
  badgeTone,
  description,
}: {
  title: string;
  badgeTone: "success" | "danger";
  description: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        <Badge tone={badgeTone}>{badgeTone === "success" ? "Income" : "Expense"}</Badge>
      </div>
      <p className="mt-2 text-sm text-muted">{description}</p>
      <div className="mt-4">
        <EmptyState
          icon={badgeTone === "success" ? TrendingUp : TrendingDown}
          title={`No ${title.toLowerCase()} categories`}
          description="Categories you create will be grouped here by type."
        />
      </div>
    </Card>
  );
}

export default function CategoriesPage() {
  const [showAddNote, setShowAddNote] = useState(false);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Categories"
        description="Organize your spending and income into categories for clearer analysis."
        actions={
          <Button onClick={() => setShowAddNote((v) => !v)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Category
          </Button>
        }
      />

      {showAddNote && (
        <Card className="border-accent-500/25 bg-accent-500/5 p-4">
          <p className="text-sm text-foreground">
            Creating categories requires an authenticated session, planned for a
            later milestone. No changes were submitted.
          </p>
        </Card>
      )}

      <section aria-labelledby="categories-overview">
        <SectionHeading
          title="Category Overview"
          description="Income and expense categories used to organize your transactions."
        />

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <CategoryGroup
            title="Income"
            badgeTone="success"
            description="Sources of money coming into your finances."
          />
          <CategoryGroup
            title="Expense"
            badgeTone="danger"
            description="Spending categories your expenses are grouped into."
          />
        </div>
      </section>

      <section aria-labelledby="available-categories">
        <SectionHeading
          title="All Categories"
          description="Every category, labeled by its type."
        />
        <Card className="mt-4 p-5">
          <EmptyState
            icon={Tags}
            title="No categories yet"
            description="When categories are set up, they will be listed here with income and expense badges."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowAddNote((v) => !v)}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                Create a category
              </Button>
            }
          />
        </Card>
      </section>
    </div>
  );
}
