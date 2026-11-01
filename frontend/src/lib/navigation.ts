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
  Building2,
  ShieldCheck,
  Users,
  GitCompareArrows,
} from "lucide-react";
import type { NavItem } from "../types/navigation";

export const adminNavigation: NavItem[] = [
  {
    label: "Admin Dashboard",
    to: "/admin",
    icon: ShieldCheck,
    allowedRoles: ["PLATFORM_ADMIN"],
  },
  {
    label: "User Management",
    to: "/admin/users",
    icon: Users,
    allowedRoles: ["PLATFORM_ADMIN"],
  },
];

const FINANCIAL_ROLES = ["MERCHANT", "FINANCE_MANAGER"] as const;

export const mainNavigation: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Accounts", to: "/accounts", icon: Wallet, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Transactions", to: "/transactions", icon: ArrowLeftRight, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Categories", to: "/categories", icon: Tags, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Budgets", to: "/budgets", icon: PiggyBank, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Goals", to: "/goals", icon: Target, allowedRoles: [...FINANCIAL_ROLES] },
  {
    label: "Businesses",
    to: "/businesses",
    icon: Building2,
    allowedRoles: ["MERCHANT"],
  },
];

export const aiNavigation: NavItem[] = [
  { label: "AI Controller", to: "/ai-controller", icon: Sparkles, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "AI Analysis", to: "/ai-analysis", icon: BrainCircuit, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Risks", to: "/risks", icon: ShieldAlert, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Recommendations", to: "/recommendations", icon: ThumbsUp, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Reconciliation", to: "/reconcile", icon: GitCompareArrows, allowedRoles: [...FINANCIAL_ROLES] },
  { label: "Audit", to: "/audit", icon: ScrollText, allowedRoles: [...FINANCIAL_ROLES] },
];

export const footerNavigation: NavItem[] = [
  { label: "Settings", to: "/settings", icon: Settings },
];
