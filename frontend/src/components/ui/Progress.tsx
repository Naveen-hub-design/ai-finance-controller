import { cn } from "../../lib/cn";

interface ProgressProps {
  value: number;
  tone?: "accent" | "success" | "warning" | "danger";
  className?: string;
}

const barClasses: Record<NonNullable<ProgressProps["tone"]>, string> = {
  accent: "bg-accent-500",
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
};

export function Progress({
  value,
  tone = "accent",
  className,
}: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="progress"
      className={cn(
        "h-2 w-full overflow-hidden rounded-full bg-surface-raised",
        className
      )}
    >
      <div
        className={cn("h-full rounded-full transition-all duration-300", barClasses[tone])}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
