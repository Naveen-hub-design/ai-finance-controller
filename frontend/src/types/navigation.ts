import type { LucideIcon } from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  end?: boolean;
}

export interface PageMeta {
  title: string;
  description: string;
}
