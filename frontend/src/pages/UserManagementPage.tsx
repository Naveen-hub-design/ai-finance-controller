import { useCallback, useEffect, useRef, useState } from "react";
import {
  Users as UsersIcon,
  Loader2,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, type ApiError } from "../lib/api";
import type { Role, User, UsersResponse } from "../lib/types";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";

const ROLE_LABELS: Record<Role, string> = {
  PLATFORM_ADMIN: "Platform Admin",
  MERCHANT: "Merchant",
  FINANCE_MANAGER: "Finance Manager",
};

const ROLE_TONES: Record<Role, "accent" | "neutral" | "warning"> = {
  PLATFORM_ADMIN: "accent",
  MERCHANT: "neutral",
  FINANCE_MANAGER: "warning",
};

interface LoadState {
  status: "loading" | "success" | "error";
  users?: User[];
  message?: string;
}

const selectClass =
  "h-9 rounded-lg border border-border bg-surface px-2.5 text-sm text-foreground transition-colors duration-150 hover:border-border-strong focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none";

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleDateString();
}

export default function UserManagementPage() {
  const { user: currentUser } = useAuth();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  const load = useCallback(async () => {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const res = await api.get<UsersResponse>("/users");
      if (cancelledRef.current) return;
      setState({ status: "success", users: res.users ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to load users.",
      });
    }
  }, []);

  useEffect(() => {
    load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const handleRoleChange = async (user: User, role: Role) => {
    if (role === user.role || updatingId) return;
    setUpdatingId(user.id);
    setUpdateError(null);
    try {
      await api.patch<{ user: User }>(`/users/${user.id}/role`, { role });
      setState((prev) => {
        if (prev.status !== "success") return prev;
        return {
          status: "success",
          users: (prev.users ?? []).map((u) =>
            u.id === user.id ? { ...u, role } : u
          ),
        };
      });
    } catch (err: unknown) {
      const e = err as ApiError;
      setUpdateError(e.message || "Unable to update the role.");
    } finally {
      setUpdatingId(null);
    }
  };

  const users = state.status === "success" ? state.users ?? [] : [];
  const counts = {
    PLATFORM_ADMIN: users.filter((u) => u.role === "PLATFORM_ADMIN").length,
    MERCHANT: users.filter((u) => u.role === "MERCHANT").length,
    FINANCE_MANAGER: users.filter((u) => u.role === "FINANCE_MANAGER").length,
  };
  const isAdmin = currentUser?.role === "PLATFORM_ADMIN";

  return (
    <div className="space-y-8">
      <PageHeader
        title="User Management"
        description="Platform-wide user accounts and role assignment."
      />

      <Card className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4">
        <span className="flex items-center gap-2 text-sm text-muted">
          <UsersIcon className="h-4 w-4 text-accent-400" aria-hidden="true" />
          <span className="font-medium text-foreground">{users.length}</span> total
        </span>
        <span className="text-sm text-muted">
          {counts.MERCHANT} Merchant · {counts.FINANCE_MANAGER} Finance Manager ·{" "}
          {counts.PLATFORM_ADMIN} Platform Admin
        </span>
      </Card>

      {state.status === "loading" && (
        <Card className="flex items-center justify-center gap-2.5 py-10 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span className="text-sm">Loading users…</span>
        </Card>
      )}

      {state.status === "error" && (
        <Card className="border-danger-500/25 bg-danger-500/5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" aria-hidden="true" />
              <div className="text-sm leading-relaxed text-foreground">
                <p className="font-medium">Unable to load users.</p>
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
        <section aria-labelledby="users-heading">
          <SectionHeading
            id="users-heading"
            title="All users"
            description="Change a user's application role. A platform admin cannot demote the last remaining platform admin."
          />
          <Card className="mt-4">
            {users.length === 0 ? (
              <EmptyState
                icon={UsersIcon}
                title="No users"
                description="No user accounts have been created yet."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-faint">
                      <th scope="col" className="px-5 py-3 font-medium">
                        User
                      </th>
                      <th scope="col" className="px-5 py-3 font-medium">
                        Role
                      </th>
                      <th scope="col" className="px-5 py-3 font-medium">
                        Joined
                      </th>
                      <th scope="col" className="px-5 py-3 text-right font-medium">
                        Assign role
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
                          <Badge tone={ROLE_TONES[u.role]}>
                            {ROLE_LABELS[u.role] ?? u.role}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 text-muted">
                          {formatTimestamp(u.created_at)}
                        </td>
                        <td className="px-5 py-3 text-right">
                          {u.id === currentUser?.id ? (
                            <span className="inline-flex items-center gap-1 text-xs text-muted">
                              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                              Current user
                            </span>
                          ) : (
                            <select
                              aria-label={`Assign role for ${u.email}`}
                              className={selectClass}
                              value={u.role}
                              disabled={updatingId === u.id}
                              onChange={(e) =>
                                handleRoleChange(u, e.target.value as Role)
                              }
                            >
                              {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                                <option key={r} value={r}>
                                  {ROLE_LABELS[r]}
                                </option>
                              ))}
                            </select>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {updateError && (
              <p className="border-t border-border px-5 py-3 text-sm text-danger-400">
                {updateError}
              </p>
            )}
          </Card>
        </section>
      )}

      {!isAdmin && (
        <Card className="border-danger-500/25 bg-danger-500/5">
          <p className="text-sm text-foreground">
            You do not have permission to manage users. This page is reserved
            for platform administrators.
          </p>
        </Card>
      )}
    </div>
  );
}
