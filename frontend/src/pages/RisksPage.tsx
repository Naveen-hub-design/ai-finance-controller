import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

const SEVERITY_TONES = [
  { label: "Critical", tone: "danger" as const },
  { label: "High", tone: "warning" as const },
  { label: "Medium", tone: "accent" as const },
  { label: "Low", tone: "neutral" as const },
];

export default function RisksPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Risks"
        description="Anomaly detection and risk flags surfaced from your financial activity."
        actions={
          <Button variant="secondary">
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <section aria-labelledby="risk-overview">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label="Total Signals"
            icon={Activity}
            value={<span className="text-muted">Unavailable</span>}
            hint="Risk signals detected across your accounts"
          />
          <StatCard
            label="Overall Grade"
            icon={ShieldCheck}
            value={<span className="text-muted">Unavailable</span>}
            hint="Aggregate health score for your finances"
          />
        </div>
      </section>

      <section aria-labelledby="risk-list">
        <SectionHeading
          title="Detected Risks"
          description="Each signal includes a severity, explanation, and the area it affects."
        />

        <Card className="mt-4 p-5">
          <EmptyState
            icon={ShieldAlert}
            title="No risk signals"
            description="Once your financial activity is analyzed, anomalies and risks will be listed here with severity badges and explanations."
          />
        </Card>
      </section>

      <section aria-labelledby="severity-legend">
        <SectionHeading
          title="Severity Levels"
          description="How individual risk signals are graded."
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SEVERITY_TONES.map((s) => (
            <Card key={s.label} className="flex items-center justify-between p-4">
              <span className="text-sm font-medium text-foreground">
                {s.label}
              </span>
              <Badge tone={s.tone}>{s.label}</Badge>
            </Card>
          ))}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
          Signal results load from the risk intelligence service; errors from a
          failed load are shown in place of the list.
        </p>
      </section>
    </div>
  );
}
