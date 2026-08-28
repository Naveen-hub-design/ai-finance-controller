import type { LucideIcon } from "lucide-react";
import { Hammer } from "lucide-react";
import { Card, CardHeader, CardTitle } from "./Card";

interface PlaceholderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
}

export function Placeholder({
  title,
  description,
  icon: Icon = Hammer,
}: PlaceholderProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed border-border-strong bg-surface-raised/40 p-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">
            Module foundation ready
          </p>
          <p className="mt-1 text-sm text-muted">
            {description ??
              "This module will be implemented in a future milestone. The engineering foundation, routing, and design system are in place."}
          </p>
        </div>
      </div>
    </Card>
  );
}
