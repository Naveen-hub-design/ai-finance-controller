import { useCallback, useEffect, useRef, useState } from "react";
import { Target, Plus, CalendarDays, Info, RefreshCw, Loader2, RotateCcw, PiggyBank, Pencil, Trash2, X } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { Progress } from "../components/ui/Progress";
import { goalStatusLabels, goalStatusTones } from "../lib/labels";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type { FinancialGoal, FinancialGoalsResponse, GoalStatus } from "../lib/types";
import { formatCurrency, formatPercent, formatDate } from "../lib/format";

const statusKeys = Object.keys(goalStatusLabels) as Array<keyof typeof goalStatusLabels>;
type LoadState = { status: "loading" } | { status: "success"; goals: FinancialGoal[] } | { status: "error"; message: string };
function toNumberSafely(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}
function isDateInPast(value: string | null): boolean {
  if (!value) return false;
  const d = new Date(value);
  return !Number.isNaN(d.getTime()) && d.getTime() < Date.now();
}
function GoalCard({ goal, onEdit, onDelete }: { goal: FinancialGoal; onEdit: () => void; onDelete: () => void; }) {
  const target = toNumberSafely(goal.target_amount) ?? 0;
  const current = toNumberSafely(goal.current_amount) ?? 0;
  const progress = target > 0 ? (current / target) * 100 : 0;
  const remaining = target - current;
  const isCompleted = goal.status === "completed" || (goal.status !== "cancelled" && target > 0 && current >= target);
  const overdue = goal.status === "active" && !isCompleted && isDateInPast(goal.target_date);
  const progressTone = isCompleted || progress >= 100 ? "success" : overdue ? "danger" : progress >= 90 ? "warning" : "accent";
  return (
    <Card className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400"><Target className="h-5 w-5" aria-hidden="true" /></div>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-medium text-foreground">{goal.name || "Untitled goal"}</h3>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-faint"><CalendarDays className="h-3 w-3" aria-hidden="true" />{goal.target_date ? `Target ${formatDate(goal.target_date)}` : "No target date"}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Badge tone={goalStatusTones[goal.status]}>{goalStatusLabels[goal.status]}</Badge>
          <Button variant="ghost" size="sm" onClick={onEdit} title="Edit"><Pencil className="h-3 w-3" /></Button>
          <Button variant="ghost" size="sm" onClick={onDelete} title="Delete"><Trash2 className="h-3 w-3 text-danger-400" /></Button>
        </div>
      </div>
      {overdue && <span className="mt-1 text-xs font-medium text-danger-400">Overdue</span>}
      <div className="mt-4 flex items-end justify-between gap-3">
        <div><p className="text-xs text-muted">Current</p><p className="text-xl font-semibold tabular-nums tracking-tight text-foreground">{formatCurrency(current)}</p></div>
        <div className="text-right"><p className="text-xs text-muted">Target</p><p className="text-xl font-semibold tabular-nums tracking-tight text-foreground">{formatCurrency(target)}</p></div>
      </div>
      <div className="mt-4 flex-1 space-y-2">
        <Progress value={progress} tone={progressTone} />
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">{remaining > 0 ? `Remaining ${formatCurrency(remaining)}` : "Goal reached"}</span>
          <span className="font-medium tabular-nums text-foreground">{formatPercent(progress)}</span>
        </div>
      </div>
      {overdue && <p className="mt-3 text-xs leading-relaxed text-muted-faint">This goal is still active and its target date has passed without being reached.</p>}
    </Card>
  );
}

export default function GoalsPage() {
  const { user } = useAuth();
  const { businessQuery, selectedBusinessId, isBusinessScope } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<FinancialGoal | null>(null);
  const [form, setForm] = useState({ name: "", target_amount: "", current_amount: "0", target_date: "", status: "active" as GoalStatus });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) { setState({ status: "error", message: "You must be signed in to view your financial goals." }); return; }
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const res = await api.get<FinancialGoalsResponse>(`/users/${user.id}/financial-goals${businessQuery()}`);
      if (cancelledRef.current) return;
      setState({ status: "success", goals: res.financial_goals ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({ status: "error", message: e.status === 403 ? "Access denied for this business." : e.message || "Unable to load your financial goals." });
    }
  }, [user, businessQuery]);
  useEffect(() => { load(); return () => { cancelledRef.current = true; }; }, [load]);
  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const res = await api.get<FinancialGoalsResponse>(`/users/${user.id}/financial-goals${businessQuery()}`);
      if (cancelledRef.current) return;
      setState({ status: "success", goals: res.financial_goals ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({ status: "error", message: e.message || "Unable to refresh your financial goals." });
    } finally { if (!cancelledRef.current) setRefreshing(false); }
  }, [user, businessQuery]);

  const openCreate = () => { setEditing(null); setForm({ name: "", target_amount: "", current_amount: "0", target_date: "", status: "active" }); setFormError(null); setShowForm(true); };
  const openEdit = (g: FinancialGoal) => { setEditing(g); setForm({ name: g.name, target_amount: g.target_amount, current_amount: g.current_amount, target_date: g.target_date ?? "", status: g.status }); setFormError(null); setShowForm(true); };
  const handleSave = async () => {
    if (!form.name.trim()) { setFormError("Name is required."); return; }
    const target = Number(form.target_amount);
    if (!Number.isFinite(target) || target <= 0) { setFormError("Target amount must be a positive number."); return; }
    const current = Number(form.current_amount);
    if (!Number.isFinite(current) || current < 0) { setFormError("Current amount must be >= 0."); return; }
    setSaving(true); setFormError(null);
    try {
      const body: Record<string, unknown> = { name: form.name.trim(), target_amount: String(target), current_amount: String(current), status: form.status };
      if (form.target_date) body.target_date = form.target_date;
      if (!editing && isBusinessScope && selectedBusinessId) body.business_id = selectedBusinessId;
      if (editing) await api.put(`/financial-goals/${editing.id}`, body);
      else await api.post("/financial-goals", body);
      setShowForm(false); await refresh();
    } catch (err: unknown) { setFormError((err as ApiError).message || "Save failed."); } finally { setSaving(false); }
  };
  const handleDelete = async (g: FinancialGoal) => {
    if (!confirm(`Delete goal "${g.name}"?`)) return;
    try { await api.delete(`/financial-goals/${g.id}`); await refresh(); } catch (err: unknown) { alert((err as ApiError).message || "Delete failed."); }
  };

  const goals = state.status === "success" ? state.goals : [];
  const activeGoals = goals.filter((g) => g.status === "active").length;
  const totalSaved = goals.reduce((sum, g) => { const n = toNumberSafely(g.current_amount); return sum + (n === null ? 0 : n); }, 0);

  return (
    <div className="space-y-8">
      <PageHeader title="Goals" description="Track progress toward your savings and financial goals."
        actions={<div className="flex items-center gap-2">
          <Button variant="secondary" onClick={refresh} disabled={refreshing || state.status === "loading"} title="Refresh goals"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />Refresh</Button>
          <Button onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Create Goal</Button>
        </div>} />

      {showForm && (
        <Card className="border-accent-500/25">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-foreground">{editing ? "Edit Goal" : "New Goal"}</h3><Button variant="ghost" size="sm" onClick={() => setShowForm(false)}><X className="h-4 w-4" /></Button></div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-1 sm:col-span-2"><span className="text-xs text-muted">Name *</span><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Emergency Fund" /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Target Amount *</span><Input type="number" step="0.01" value={form.target_amount} onChange={(e) => setForm({ ...form, target_amount: e.target.value })} placeholder="100000" /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Current Amount</span><Input type="number" step="0.01" value={form.current_amount} onChange={(e) => setForm({ ...form, current_amount: e.target.value })} /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Target Date</span><Input type="date" value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Status</span>
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as GoalStatus })} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm">
                {(Object.keys(goalStatusLabels) as GoalStatus[]).map((s) => <option key={s} value={s}>{goalStatusLabels[s]}</option>)}
              </select>
            </label>
          </div>
          {isBusinessScope && <p className="mt-2 text-xs text-muted-faint">Will be created in the selected business.</p>}
          {formError && <p className="mt-3 flex items-center gap-1.5 text-sm text-danger-400"><Info className="h-4 w-4" />{formError}</p>}
          <div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => setShowForm(false)} disabled={saving}>Cancel</Button><Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{editing ? "Update" : "Create"}</Button></div>
        </Card>
      )}

      <section aria-label="Goals summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Active Goals" icon={Target} value={state.status === "success" ? activeGoals : "—"} hint="Goals you are currently working toward" />
        <StatCard label="Total Saved" icon={PiggyBank} value={state.status === "success" ? formatCurrency(totalSaved) : "—"} hint="Sum across all goal current amounts" />
      </section>

      <section aria-labelledby="goals-list-heading">
        <SectionHeading id="goals-list-heading" title="Your Goals" description="Each goal shows its target and current amount, target date, status, and progress." />
        {state.status === "loading" && <Card className="mt-4 flex items-center gap-3 p-6"><Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" /><p className="text-sm text-muted">Loading your goals…</p></Card>}
        {state.status === "error" && <div className="mt-4"><EmptyState icon={Target} title="Could not load goals" description={state.message} action={<Button variant="secondary" size="sm" onClick={load}><RotateCcw className="h-4 w-4" aria-hidden="true" />Retry</Button>} /></div>}
        {state.status === "success" && goals.length === 0 && <Card className="mt-4"><EmptyState icon={Target} title="No goals yet" description="Create your first goal to get started." action={<Button variant="secondary" size="sm" onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Create your first goal</Button>} /></Card>}
        {state.status === "success" && goals.length > 0 && <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{goals.map((g) => <GoalCard key={g.id} goal={g} onEdit={() => openEdit(g)} onDelete={() => handleDelete(g)} />)}</div>}
      </section>

      <section aria-labelledby="goal-statuses-heading">
        <SectionHeading id="goal-statuses-heading" title="Goal Statuses" description="Goals are labeled by their current lifecycle status." />
        <div className="mt-4 flex flex-wrap gap-2">{statusKeys.map((status) => <Badge key={status} tone={goalStatusTones[status]}><CalendarDays className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />{goalStatusLabels[status]}</Badge>)}</div>
      </section>
    </div>
  );
}
