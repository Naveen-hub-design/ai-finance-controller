import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const toneClasses: Record<Tone, string> = {
  neutral: "bg-surface-raised text-muted border-border",
  accent: "bg-accent-500/10 text-accent-300 border-accent-500/25",
  success: "bg-success-500/10 text-success-500 border-success-500/25",
  warning: "bg-warning-500/10 text-warning-500 border-warning-500/25",
  danger: "bg-danger-500/10 text-danger-400 border-danger-500/25",
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
