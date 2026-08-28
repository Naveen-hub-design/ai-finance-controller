import { Link, useParams } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  ArrowLeft,
  Receipt,
  Pencil,
  Trash2,
  Hash,
  CalendarDays,
  Tag,
  Building2,
  Folder,
  CircleDollarSign,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

function DetailRow({
  icon: Icon,
  label,
  value,
  valueClassName,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border py-3 last:border-b-0">
      <div className="flex items-center gap-2 text-muted">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span className="text-sm">{label}</span>
      </div>
      <span className={"text-sm text-foreground " + (valueClassName ?? "")}>
        {value}
      </span>
    </div>
  );
}

export default function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const shortId = id ? `${id.slice(0, 8)}…` : "—";

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/transactions"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to transactions
        </Link>
        <PageHeader
          title="Transaction Details"
          description={`Reviewing transaction ${id ? `#${id}` : "detail"}.`}
          actions={
            <>
              <Button variant="secondary">
                <Pencil className="h-4 w-4" aria-hidden="true" />
                Edit
              </Button>
              <Button variant="danger">
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete
              </Button>
            </>
          }
        />
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-raised text-accent-400">
            <Receipt className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <p className="text-lg font-semibold tracking-tight text-foreground">
              Transaction {shortId}
            </p>
            <Badge tone="neutral" className="mt-1">
              Awaiting data
            </Badge>
          </div>
        </div>

        <div className="mt-5">
          <DetailRow
            icon={Hash}
            label="Transaction ID"
            value={id ? shortId : "—"}
          />
          <DetailRow
            icon={CircleDollarSign}
            label="Amount"
            value="Unavailable"
            valueClassName="text-lg font-semibold"
          />
          <DetailRow
            icon={CalendarDays}
            label="Date"
            value="Unavailable"
          />
          <DetailRow icon={Receipt} label="Description" value="Unavailable" />
          <DetailRow
            icon={Building2}
            label="Account"
            value="Unavailable"
          />
          <DetailRow icon={Folder} label="Category" value="Unavailable" />
          <DetailRow icon={Tag} label="Type" value="Unavailable" />
        </div>

        <p className="mt-5 text-xs leading-relaxed text-muted-faint">
          This detail view is ready to load a transaction by its ID from the
          backend. Data binding is deferred until the API integration layer and
          authentication are in place. The Edit and Delete actions are shown
          for structure and are not connected to any backend request yet.
        </p>
      </Card>
    </div>
  );
}
