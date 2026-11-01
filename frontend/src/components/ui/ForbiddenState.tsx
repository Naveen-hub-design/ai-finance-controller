import { ShieldAlert, type LucideIcon } from "lucide-react";
import { Card } from "./Card";

interface ForbiddenStateProps {
  title?: string;
  description?: string;
  icon?: LucideIcon;
}

/**
 * Clean, consistent "not authorized" state shown when the backend returns 403
 * for an otherwise-valid request. Never exposes stack traces and never fakes
 * data for a forbidden resource.
 */
export function ForbiddenState({
  title = "You don't have permission to access this resource.",
  description = "Your current role does not allow this. If you believe this is a mistake, contact your administrator.",
  icon: Icon = ShieldAlert,
}: ForbiddenStateProps) {
  return (
    <Card
      role="alert"
      className="border-danger-500/25 bg-danger-500/5"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-danger-400">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="mt-1.5 text-sm leading-relaxed text-muted">
            {description}
          </p>
        </div>
      </div>
    </Card>
  );
}
