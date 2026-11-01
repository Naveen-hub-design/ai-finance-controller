import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ScrollText,
  History,
  ShieldAlert,
  FileCheck2,
  Scale,
  Loader2,
  AlertTriangle,
  ListChecks,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { ForbiddenState } from "../components/ui/ForbiddenState";
import {
  auditKindLabels,
  auditKindTones,
} from "../lib/labels";
import type { AuditKind, AuditRecord } from "../lib/types";

const EVENT_TYPES: {
  key: AuditKind;
  icon: LucideIcon;
  description: string;
}[] = [
  {
    key: "decision",
    icon: Scale,
    description: "Decisions the controller made on your behalf.",
  },
  {
    key: "risk",
    icon: ShieldAlert,
    description: "Risk signals flagged during analysis.",
  },
  {
    key: "recommendation",
    icon: FileCheck2,
    description: "Suggestions generated for your finances.",
  },
  {
    key: "reconciliation",
    icon: ListChecks,
    description: "Ledger-to-statement reconciliation batches run for your business.",
  },
];

interface LoadState {
  status: "loading" | "success" | "forbidden" | "error";
  records?: AuditRecord[];
  message?: string;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return date.toLocaleString();
}

export default function AuditPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view the audit trail.",
      });
      return;
    }

    cancelledRef.current = false;
    setState({ status: "loading" });

    try {
      const res = await api.get<{ records: AuditRecord[] }>(
        `/users/${user.id}/audit${businessQuery()}`
      );
      if (cancelledRef.current) return;
      setState({ status: "success", records: res.records ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      if (e.status === 403) {
        setState({ status: "forbidden" });
        return;
      }
      setState({
        status: "error",
        message: e.message || "Unable to load the audit trail.",
      });
    }
  }, [user, businessQuery]);

  useEffect(() => {
    load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const records = state.status === "success" ? state.records ?? [] : [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Audit"
        description="A chronological record of AI-generated decisions, risks, recommendations, and reconciliations."
      />

      {state.status === "loading" && (
        <Card className="flex items-center justify-center gap-2.5 py-10 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span className="text-sm">Loading audit events…</span>
        </Card>
      )}

      {state.status === "forbidden" && <ForbiddenState />}

      {state.status === "error" && (
        <Card className="border-danger-500/25 bg-danger-500/5">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" aria-hidden="true" />
            <div className="text-sm leading-relaxed text-foreground">
              <p className="font-medium">Unable to load audit events.</p>
              {state.message && <p className="mt-1 text-muted">{state.message}</p>}
            </div>
          </div>
        </Card>
      )}

      {state.status === "success" && (
        <section aria-labelledby="audit-timeline-heading">
          <SectionHeading
            id="audit-timeline-heading"
            title="Audit Timeline"
            description="Events are shown newest first with their type badge and timestamp."
          />

          <Card className="mt-4">
            {records.length === 0 ? (
              <EmptyState
                icon={History}
                title="No audit events"
                description="AI decisions, risk signals, and recommendations will appear here in chronological order as they are generated."
              />
            ) : (
              <ul className="divide-y divide-border">
                {records.map((record) => (
                  <li key={record.id} className="flex flex-col gap-1.5 py-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={auditKindTones[record.kind]}>
                          {auditKindLabels[record.kind] ?? record.kind}
                        </Badge>
                        <span className="text-xs text-muted-faint">
                          {formatTimestamp(record.created_at)}
                        </span>
                      </div>
                      <p className="mt-1.5 text-sm text-muted">
                        {record.payload && typeof record.payload === "object" ? (
                          <span className="block whitespace-pre-wrap">
                            {JSON.stringify(record.payload, null, 2)}
                          </span>
                        ) : (
                          "No additional metadata."
                        )}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>
      )}

      <section aria-labelledby="audit-types-heading">
        <SectionHeading
          id="audit-types-heading"
          title="Event Types"
          description="The kinds of events recorded in the audit trail."
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {EVENT_TYPES.map((evt) => (
            <Card key={evt.key} className="card-interactive flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                  <evt.icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <Badge tone={auditKindTones[evt.key]}>
                  {auditKindLabels[evt.key]}
                </Badge>
              </div>
              <p className="text-sm text-muted">{evt.description}</p>
            </Card>
          ))}
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
          <ScrollText className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          The audit trail is append-only: decisions, risks, recommendations,
          and reconciliations are recorded and read back in time order.
        </p>
      </section>
    </div>
  );
}
