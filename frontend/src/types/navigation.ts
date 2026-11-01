import type { LucideIcon } from "lucide-react";
import type { Role } from "../lib/types";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  end?: boolean;
  /** Only users with one of these roles see this item. */
  allowedRoles?: Role[];
}
