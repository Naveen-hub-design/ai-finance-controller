import { ScrollText, History, ShieldAlert, FileCheck2, Scale } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { auditKindLabels } from "../lib/labels";

const EVENT_TYPES = [
  { key: "decision", icon: Scale, badge: "decision" },
  { key: "risk", icon: ShieldAlert, badge: "risk" },
  { key: "recommendation", icon: FileCheck2, badge: "recommendation" },
] as const;

export default function AuditPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Audit"
        description="A chronological record of AI-generated decisions, risks, and recommendations."
      />

      <Card className="border-accent-500/25 bg-accent-500/5 p-4">
        <p className="text-sm leading-relaxed text-foreground">
          The audit trail is not yet available: the underlying records are not
          present in the current environment. No entries are shown until the
          audit storage is provisioned and the API is connected.
        </p>
      </Card>

      <section aria-labelledby="audit-timeline">
        <SectionHeading
          title="Audit Timeline"
          description="Events are shown newest first with their type badge and timestamp."
        />

        <Card className="mt-4 p-5">
          <EmptyState
            icon={History}
            title="No audit events"
            description="AI decisions, risk signals, and recommendations will appear here in chronological order once the audit trail is available."
          />
        </Card>
      </section>

      <section aria-labelledby="audit-types">
        <SectionHeading
          title="Event Types"
          description="The kinds of events recorded in the audit trail."
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {EVENT_TYPES.map((evt) => (
            <Card key={evt.key} className="flex items-center gap-3 p-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                <evt.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">
                  {auditKindLabels[evt.badge]}
                </span>
                <Badge
                  tone={
                    evt.badge === "decision"
                      ? "accent"
                      : evt.badge === "risk"
                      ? "danger"
                      : "success"
                  }
                >
                  {auditKindLabels[evt.badge]}
                </Badge>
              </div>
            </Card>
          ))}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
          <ScrollText className="h-3.5 w-3.5" aria-hidden="true" />
          The audit trail is append-only: decisions, risks, and recommendations
          are recorded and read back in time order.
        </p>
      </section>
    </div>
  );
}
