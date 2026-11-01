import { useCallback, useEffect, useRef, useState } from "react";
import {
  Building2,
  Plus,
  Loader2,
  UserPlus,
  Trash2,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { SectionHeading } from "../components/ui/SectionHeading";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { api, type ApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import type {
  BusinessMember,
  BusinessMemberRole,
  BusinessMembersResponse,
  BusinessesResponse,
  BusinessWithRole,
} from "../lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "success"; businesses: BusinessWithRole[] }
  | { status: "error"; message: string };

function MemberRow({
  member,
  canManage,
  onRemove,
  removing,
}: {
  member: BusinessMember;
  canManage: boolean;
  onRemove: (member: BusinessMember) => void;
  removing: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-5 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
          <UserIcon className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {member.full_name || member.email || member.user_id}
          </p>
          <p className="truncate text-xs text-muted-faint">{member.email}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge tone={member.role === "OWNER" ? "accent" : "neutral"}>
          {member.role}
        </Badge>
        {canManage && member.role !== "OWNER" && (
          <Button
            variant="ghost"
            size="sm"
            disabled={removing}
            aria-label={`Remove ${member.email ?? member.user_id}`}
            onClick={() => onRemove(member)}
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}
      </div>
    </div>
  );
}

export default function BusinessesPage() {
  const { user } = useAuth();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [active, setActive] = useState<BusinessWithRole | null>(null);
  const [members, setMembers] = useState<BusinessMember[]>([]);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState<BusinessMemberRole>(
    "FINANCE_MANAGER"
  );
  const [adding, setAdding] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  const canManage = active?.my_role === "OWNER";

  const loadBusinesses = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view businesses.",
      });
      return;
    }
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const res = await api.get<BusinessesResponse>("/businesses");
      if (cancelledRef.current) return;
      const businesses = res.businesses ?? [];
      setState({ status: "success", businesses });
      // Re-hydrate the active selection after refresh.
      setActive((prev) => {
        if (!prev) return businesses[0] ?? null;
        return businesses.find((b) => b.id === prev.id) ?? null;
      });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to load your businesses.",
      });
    }
  }, [user]);

  const loadMembers = useCallback(async (businessId: string) => {
    try {
      const res = await api.get<BusinessMembersResponse>(
        `/businesses/${businessId}/members`
      );
      if (cancelledRef.current) return;
      setMembers(res.members ?? []);
    } catch {
      if (!cancelledRef.current) setMembers([]);
    }
  }, []);

  useEffect(() => {
    loadBusinesses();
    return () => {
      cancelledRef.current = true;
    };
  }, [loadBusinesses]);

  useEffect(() => {
    if (active) {
      setMembers([]);
      loadMembers(active.id);
    } else {
      setMembers([]);
    }
  }, [active, loadMembers]);

  const createBusiness = async () => {
    if (!newName.trim()) {
      setError("Business name is required.");
      return;
    }
    setCreating(true);
    setError(null);
    setInfo(null);
    try {
      await api.post("/businesses", { name: newName.trim() });
      setNewName("");
      setInfo("Business created.");
      await loadBusinesses();
    } catch (err: unknown) {
      const e = err as ApiError;
      setError(e.message || "Unable to create business.");
    } finally {
      setCreating(false);
    }
  };

  const addMember = async () => {
    if (!active) return;
    if (!memberEmail.trim()) {
      setError("A member email is required.");
      return;
    }
    setAdding(true);
    setError(null);
    setInfo(null);
    try {
      // Adding by email is resolved server-side, so an OWNER never needs
      // access to the (PLATFORM_ADMIN-only) user directory.
      await api.post(`/businesses/${active.id}/members`, {
        email: memberEmail.trim(),
        role: memberRole,
      });
      setMemberEmail("");
      setInfo("Member added.");
      await loadMembers(active.id);
    } catch (err: unknown) {
      const e = err as ApiError;
      setError(e.message || "Unable to add member.");
    } finally {
      setAdding(false);
    }
  };

  const removeMember = async (member: BusinessMember) => {
    if (!active) return;
    setRemovingId(member.user_id);
    setError(null);
    setInfo(null);
    try {
      await api.delete(`/businesses/${active.id}/members/${member.user_id}`);
      setInfo("Member removed.");
      await loadMembers(active.id);
    } catch (err: unknown) {
      const e = err as ApiError;
      setError(e.message || "Unable to remove member.");
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Businesses"
        description="Create and manage business workspaces and their members."
      />

      <section aria-labelledby="create-business-section">
        <SectionHeading
          id="create-business-section"
          title="Create a business"
          description="You become the owner of any business you create."
        />
        <Card className="mt-4 p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label
                htmlFor="business-name"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Business name
              </label>
              <Input
                id="business-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Acme Ltd"
              />
            </div>
            <Button onClick={createBusiness} disabled={creating}>
              {creating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Plus className="h-4 w-4" aria-hidden="true" />
              )}
              Create business
            </Button>
          </div>
          {info && <p className="mt-3 text-sm text-success-500">{info}</p>}
          {error && <p className="mt-3 text-sm text-danger-400">{error}</p>}
        </Card>
      </section>

      {state.status === "loading" && (
        <div className="flex items-center justify-center py-16 text-muted">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-accent-400" aria-hidden="true" />
          Loading businesses…
        </div>
      )}

      {state.status === "error" && (
        <EmptyState
          icon={Building2}
          title="Unable to load businesses"
          description={state.message}
        />
      )}

      {state.status === "success" && state.businesses.length === 0 && (
        <EmptyState
          icon={Building2}
          title="No businesses yet"
          description="Create a business to start collaborating with finance managers."
        />
      )}

      {state.status === "success" && state.businesses.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section aria-labelledby="business-list-section">
            <SectionHeading
              id="business-list-section"
              title="Your businesses"
              description="Businesses you are a member of."
            />
            <Card className="mt-4 divide-y divide-border">
              {state.businesses.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => setActive(b)}
                  className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-surface-raised"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
                      <Building2 className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {b.name}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-faint">
                        {b.id.slice(0, 8)}…
                      </p>
                    </div>
                  </div>
                  <Badge tone={b.my_role === "OWNER" ? "accent" : "neutral"}>
                    {b.my_role}
                  </Badge>
                </button>
              ))}
            </Card>
          </section>

          {active && (
            <section aria-labelledby="business-detail-section">
              <SectionHeading
                id="business-detail-section"
                title={active.name}
                description={`Members of this business${
                  canManage ? " — you are the owner" : ""
                }.`}
              />
              <Card className="mt-4">
                <div className="divide-y divide-border">
                  {members.map((m) => (
                    <MemberRow
                      key={m.user_id}
                      member={m}
                      canManage={canManage}
                      removing={removingId === m.user_id}
                      onRemove={removeMember}
                    />
                  ))}
                  {members.length === 0 && (
                    <p className="px-5 py-6 text-sm text-muted-faint">
                      No members yet.
                    </p>
                  )}
                </div>

                {canManage && (
                  <div className="border-t border-border px-5 py-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                      <div className="flex-1">
                        <label
                          htmlFor="member-email"
                          className="mb-1.5 block text-sm font-medium text-muted"
                        >
                          Add member by email
                        </label>
                        <Input
                          id="member-email"
                          value={memberEmail}
                          onChange={(e) => setMemberEmail(e.target.value)}
                          placeholder="finance@example.com"
                        />
                      </div>
                      <div>
                        <label
                          htmlFor="member-role"
                          className="mb-1.5 block text-sm font-medium text-muted"
                        >
                          Role
                        </label>
                        <select
                          id="member-role"
                          className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-foreground focus:border-accent-500 focus:outline-none"
                          value={memberRole}
                          onChange={(e) =>
                            setMemberRole(e.target.value as BusinessMemberRole)
                          }
                        >
                          <option value="FINANCE_MANAGER">
                            Finance Manager
                          </option>
                        </select>
                      </div>
                      <Button onClick={addMember} disabled={adding}>
                        {adding ? (
                          <Loader2
                            className="h-4 w-4 animate-spin"
                            aria-hidden="true"
                          />
                        ) : (
                          <UserPlus className="h-4 w-4" aria-hidden="true" />
                        )}
                        Add member
                      </Button>
                    </div>
                    <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-faint">
                      <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                      Finance managers get read access to the business but cannot
                      manage members.
                    </p>
                    {info && (
                      <p className="mt-3 text-sm text-success-500">{info}</p>
                    )}
                    {error && (
                      <p className="mt-3 text-sm text-danger-400">{error}</p>
                    )}
                  </div>
                )}
              </Card>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
