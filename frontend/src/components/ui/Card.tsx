import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {}

export function Card({ className, ...props }: CardProps) {
  return <div className={cn("surface-card p-5", className)} {...props} />;
}

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {}

export function CardHeader({ className, ...props }: CardHeaderProps) {
  return <div className={cn("mb-4", className)} {...props} />;
}

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {}

export function CardTitle({ className, ...props }: CardTitleProps) {
  return (
    <h3
      className={cn(
        "text-base font-semibold tracking-tight text-foreground",
        className
      )}
      {...props}
    />
  );
}
