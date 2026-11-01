import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

interface SectionHeadingProps {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  id?: string;
}

export function SectionHeading({
  title,
  description,
  action,
  className,
  id,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between",
        className
      )}
    >
      <div>
        <h2
          id={id}
          className="text-base font-semibold tracking-tight text-foreground"
        >
          {title}
        </h2>
        {description && (
          <p className="mt-0.5 text-sm text-muted">{description}</p>
        )}
      </div>
      {action && <div className="flex items-center gap-2">{action}</div>}
    </div>
  );
}
