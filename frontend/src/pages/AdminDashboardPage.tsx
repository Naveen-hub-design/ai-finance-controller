import { useCallback, useEffect, useRef, useState } from "react";
import {
  Users as UsersIcon,
  ShieldCheck,
  Store,
  UserCog,
  Loader2,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, type ApiError } from "../lib/api";
import type { Role, User, UsersResponse } from "../lib/types";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

const ROLE_LABELS: Record<Role, string> = {
  PLATFORM_ADMIN: "Platform Admin",
  MERCHANT: "Merchant",
  FINANCE_MANAGER: "Finance Manager",
};

interface AdminStats {
  total_users: number;
  users_by_role: Record<Role, number>;
  total_businesses: number;
}

interface LoadState {
  status: "loading" | "success" | "error";
  users?: User[];
  stats?: AdminStats;
  message?: string;
}

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const [res, statsRes] = await Promise.all([
        api.get<UsersResponse>("/users"),
        api.get<AdminStats>("/admin/stats"),
      ]);
      if (cancelledRef.current) return;
      setState({
        status: "success",
        users: res.users ?? [],
        stats: statsRes,
      });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to load platform data.",
      });
    }
  }, []);

  useEffect(() => {
    load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const users = state.status === "success" ? state.users ?? [] : [];
  const stats = state.stats;
  const counts = {
    PLATFORM_ADMIN: users.filter((u) => u.role === "PLATFORM_ADMIN").length,
    MERCHANT: users.filter((u) => u.role === "MERCHANT").length,
    FINANCE_MANAGER: users.filter((u) => u.role === "FINANCE_MANAGER").length,
  };


  return (
    <div className="space-y-8">
      <PageHeader
        title="Admin Dashboard"
        description="Platform-level overview for administrators."
      />

      {state.status === "loading" && (
        <Card className="flex items-center justify-center gap-2.5 py-10 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span className="text-sm">Loading platform data…</span>
        </Card>
      )}

      {state.status === "error" && (
        <Card className="border-danger-500/25 bg-danger-500/5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" aria-hidden="true" />
              <div className="text-sm leading-relaxed text-foreground">
                <p className="font-medium">Unable to load platform data.</p>
                {state.message && <p className="mt-1 text-muted">{state.message}</p>}
              </div>
            </div>
            <Button variant="secondary" size="sm" onClick={load}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Retry
            </Button>
          </div>
        </Card>
      )}

      {state.status === "success" && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              label="Total users"
              value={stats?.total_users ?? users.length}
              icon={UsersIcon}
              hint="Registered accounts on the platform"
            />
            <StatCard
              label="Businesses"
              value={stats?.total_businesses ?? 0}
              icon={Store}
              hint="Businesses registered on the platform"
            />
            <StatCard
              label="Finance managers"
              value={stats?.users_by_role?.FINANCE_MANAGER ?? counts.FINANCE_MANAGER}
              icon={UserCog}
              hint="Finance manager role accounts"
            />
          </div>

          <section aria-labelledby="platform-users-heading">
            <SectionHeading
              id="platform-users-heading"
              title="Platform accounts"
              description="A breakdown of accounts by role."
            />
            <Card className="mt-4">
              {users.length === 0 ? (
                <EmptyState
                  icon={UsersIcon}
                  title="No users"
                  description="No accounts have been registered yet."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[560px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-faint">
                        <th scope="col" className="px-5 py-3 font-medium">
                          Account
                        </th>
                        <th scope="col" className="px-5 py-3 font-medium">
                          Role
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-surface-raised/40">
                          <td className="px-5 py-3">
                            <div className="text-sm font-medium text-foreground">
                              {u.full_name || "—"}
                            </div>
                            <div className="text-xs text-muted">{u.email}</div>
                          </td>
                          <td className="px-5 py-3">
                            {ROLE_LABELS[u.role] ?? u.role}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </section>

          <Card className="flex flex-col items-start justify-between gap-4 border-accent-500/25 bg-accent-500/5 sm:flex-row sm:items-center">
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" aria-hidden="true" />
              <div className="text-sm leading-relaxed text-foreground">
                <p className="font-medium">User management</p>
                <p className="mt-0.5 text-muted">
                  Assign and review application roles across the platform.
                  The platform dashboard reports aggregate account and business
                  counts only; it does not expose any merchant financial data.
                </p>
              </div>
            </div>
            <Link
              to="/admin/users"
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600"
            >
              Manage users
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Card>
        </>
      )}

      {user?.role !== "PLATFORM_ADMIN" && (
        <Card className="border-danger-500/25 bg-danger-500/5">
          <p className="text-sm text-foreground">
            You do not have permission to view the platform dashboard. This
            page is reserved for platform administrators.
          </p>
        </Card>
      )}
    </div>
  );
}
