import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 focus:border-accent-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);

Input.displayName = "Input";
