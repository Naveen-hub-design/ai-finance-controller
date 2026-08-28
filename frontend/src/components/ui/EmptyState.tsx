import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border-strong bg-surface-raised/30 p-8 text-center",
        className
      )}
    >
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-raised text-accent-400">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
      )}
      <div>
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        {description && (
          <p className="mx-auto mt-1 max-w-md text-sm text-muted">
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
