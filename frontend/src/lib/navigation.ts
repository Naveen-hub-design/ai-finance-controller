import {
  LayoutDashboard,
  Wallet,
  ArrowLeftRight,
  Tags,
  PiggyBank,
  Target,
  Sparkles,
  BrainCircuit,
  ShieldAlert,
  ThumbsUp,
  ScrollText,
  Settings,
} from "lucide-react";
import type { NavItem } from "../types/navigation";

export const mainNavigation: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Accounts", to: "/accounts", icon: Wallet },
  { label: "Transactions", to: "/transactions", icon: ArrowLeftRight },
  { label: "Categories", to: "/categories", icon: Tags },
  { label: "Budgets", to: "/budgets", icon: PiggyBank },
  { label: "Goals", to: "/goals", icon: Target },
];

export const aiNavigation: NavItem[] = [
  { label: "AI Controller", to: "/ai-controller", icon: Sparkles },
  { label: "AI Analysis", to: "/ai-analysis", icon: BrainCircuit },
  { label: "Risks", to: "/risks", icon: ShieldAlert },
  { label: "Recommendations", to: "/recommendations", icon: ThumbsUp },
  { label: "Audit", to: "/audit", icon: ScrollText },
];

export const footerNavigation: NavItem[] = [
  { label: "Settings", to: "/settings", icon: Settings },
];
