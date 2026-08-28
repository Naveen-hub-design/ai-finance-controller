import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  hint?: string;
  iconClassName?: string;
  className?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  iconClassName,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "surface-card flex items-start gap-4 p-5",
        className
      )}
    >
      {Icon && (
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400",
            iconClassName
          )}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-sm text-muted">{label}</p>
        <p className="mt-1 text-xl font-semibold tracking-tight text-foreground">
          {value}
        </p>
        {hint && <p className="mt-1 text-xs text-muted-faint">{hint}</p>}
      </div>
    </div>
  );
}
