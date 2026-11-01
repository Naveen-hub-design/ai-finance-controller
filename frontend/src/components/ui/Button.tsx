import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-accent-600 text-white hover:bg-accent-500 active:bg-accent-700 disabled:hover:bg-accent-600",
  secondary:
    "bg-surface-raised text-foreground border border-border hover:bg-surface-hover active:bg-surface-raised",
  ghost:
    "bg-transparent text-muted hover:text-foreground hover:bg-surface-raised",
  danger:
    "bg-danger-600 text-white hover:bg-danger-500 active:bg-danger-700",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-base gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant = "primary", size = "md", type = "button", ...props },
    ref
  ) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex select-none items-center justify-center whitespace-nowrap rounded-lg font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent-500/40 focus-visible:outline-none",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    />
  )
);

Button.displayName = "Button";
