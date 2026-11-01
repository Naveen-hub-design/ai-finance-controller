import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PiggyBank, Plus, CalendarRange, Gauge, Info, RefreshCw, Loader2, RotateCcw, Folder, Pencil, Trash2, X } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { Progress } from "../components/ui/Progress";
import { budgetPeriodLabels, budgetStatusFromProgress, budgetStatusTones } from "../lib/labels";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type { Budget, BudgetsResponse, BudgetPeriod, Category, CategoriesResponse } from "../lib/types";
import { formatCurrency, formatPercent, formatShortDate } from "../lib/format";

const STATUS_LEGEND: { label: string; key: keyof typeof budgetStatusTones }[] = [
  { label: "On track", key: "on_track" }, { label: "Near limit", key: "near_limit" }, { label: "Over", key: "over" }, { label: "Upcoming", key: "upcoming" },
];
type LoadState = { status: "loading" } | { status: "success"; budgets: Budget[] } | { status: "error"; message: string };
type BudgetStatusKey = keyof typeof budgetStatusTones;
function toNumberSafely(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}
function statusFromProgress(progress: number | null): BudgetStatusKey { return budgetStatusFromProgress(progress); }
const progressTone: Record<BudgetStatusKey, "accent" | "success" | "warning" | "danger"> = { on_track: "success", near_limit: "warning", over: "danger", upcoming: "accent" };
function shortId(id: string): string { return id.length > 8 ? `${id.slice(0, 8)}…` : id; }

function BudgetCard({
  budget,
  categoryName,
  onEdit,
  onDelete,
}: {
  budget: Budget;
  categoryName?: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const amount = toNumberSafely(budget.amount) ?? 0;
  const spent = toNumberSafely(budget.spent);
  const remaining = toNumberSafely(budget.remaining);
  const progress = toNumberSafely(budget.progress_percent);
  const status = statusFromProgress(progress);
  const hasSpendingData = spent !== null && remaining !== null && progress !== null;
  const displayCategory = categoryName || (budget.category_id ? `Category ${shortId(budget.category_id)}` : "All Categories");

  return (
    <Card className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
            <PiggyBank className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-foreground">
              {displayCategory}
            </h3>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-faint">
              <Folder className="h-3 w-3" aria-hidden="true" />
              {budgetPeriodLabels[budget.period]}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Badge tone={budgetStatusTones[status]}>{STATUS_LEGEND.find((s) => s.key === status)?.label ?? status}</Badge>
          <Button variant="ghost" size="sm" onClick={onEdit} title="Edit"><Pencil className="h-3 w-3" /></Button>
          <Button variant="ghost" size="sm" onClick={onDelete} title="Delete"><Trash2 className="h-3 w-3 text-danger-400" /></Button>
        </div>
      </div>
      <p className="mt-4 flex items-center gap-1.5 text-sm text-muted"><CalendarRange className="h-4 w-4" aria-hidden="true" />{formatShortDate(budget.start_date)} – {formatShortDate(budget.end_date)}</p>
      <div className="mt-4 flex items-end justify-between gap-3">
        <div><p className="text-xs text-muted">Budgeted</p><p className="text-xl font-semibold tabular-nums tracking-tight text-foreground">{formatCurrency(amount)}</p></div>
        {hasSpendingData && <div className="text-right"><p className="text-xs text-muted">Remaining</p><p className="text-xl font-semibold tabular-nums tracking-tight text-foreground">{formatCurrency(remaining)}</p></div>}
      </div>
      <div className="mt-4 flex-1">
        {hasSpendingData ? (
          <div className="space-y-2"><div className="flex items-center justify-between text-sm"><span className="text-muted">Spent {formatCurrency(spent)}</span><span className="font-medium tabular-nums text-foreground">{formatPercent(progress)}</span></div><Progress value={progress} tone={progressTone[status]} /></div>
        ) : <div className="rounded-lg border border-dashed border-border-strong bg-surface-raised/30 p-3 text-xs text-muted">Spending data for this period is not available yet.</div>}
      </div>
    </Card>
  );
}

export default function BudgetsPage() {
  const { user } = useAuth();
  const { businessQuery, selectedBusinessId, isBusinessScope } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Budget | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState({ category_id: "", amount: "", period: "monthly" as BudgetPeriod, start_date: new Date().toISOString().slice(0, 10), end_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10) });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) { setState({ status: "error", message: "You must be signed in to view your budgets." }); return; }
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const [res, catRes] = await Promise.all([
        api.get<BudgetsResponse>(`/users/${user.id}/budgets${businessQuery()}`),
        api.get<CategoriesResponse>(`/users/${user.id}/categories`).catch(() => ({ categories: [] })),
      ]);
      if (cancelledRef.current) return;
      setState({ status: "success", budgets: res.budgets ?? [] });
      setCategories(catRes.categories ?? []);
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({ status: "error", message: e.status === 403 ? "Access denied for this business." : e.message || "Unable to load your budgets." });
    }
  }, [user, businessQuery]);
  useEffect(() => { load(); return () => { cancelledRef.current = true; }; }, [load]);
  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const [res, catRes] = await Promise.all([
        api.get<BudgetsResponse>(`/users/${user.id}/budgets${businessQuery()}`),
        api.get<CategoriesResponse>(`/users/${user.id}/categories`).catch(() => ({ categories: [] })),
      ]);
      if (cancelledRef.current) return;
      setState({ status: "success", budgets: res.budgets ?? [] });
      setCategories(catRes.categories ?? []);
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({ status: "error", message: e.message || "Unable to refresh your budgets." });
    } finally { if (!cancelledRef.current) setRefreshing(false); }
  }, [user, businessQuery]);

  const categoriesMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of categories) map.set(c.id, c.name);
    return map;
  }, [categories]);

  const loadCats = async () => {
    if (!user) return;
    try { const r = await api.get<CategoriesResponse>(`/users/${user.id}/categories`); setCategories(r.categories ?? []); } catch { /* ignore */ }
  };
  const openCreate = async () => { setEditing(null); setForm({ category_id: "", amount: "", period: "monthly", start_date: new Date().toISOString().slice(0, 10), end_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10) }); setFormError(null); setShowForm(true); await loadCats(); };
  const openEdit = async (b: Budget) => { setEditing(b); setForm({ category_id: b.category_id ?? "", amount: b.amount, period: b.period, start_date: b.start_date, end_date: b.end_date }); setFormError(null); setShowForm(true); await loadCats(); };
  const handleSave = async () => {
    const amt = Number(form.amount);
    if (!Number.isFinite(amt) || amt <= 0) { setFormError("Amount must be a positive number."); return; }
    if (!form.start_date || !form.end_date) { setFormError("Start and end dates are required."); return; }
    if (form.end_date < form.start_date) { setFormError("End date must be after start date."); return; }
    setSaving(true); setFormError(null);
    try {
      const body: Record<string, unknown> = { amount: String(amt), period: form.period, start_date: form.start_date, end_date: form.end_date };
      if (form.category_id) body.category_id = form.category_id;
      if (!editing && isBusinessScope && selectedBusinessId) body.business_id = selectedBusinessId;
      if (editing) await api.put(`/budgets/${editing.id}`, body);
      else await api.post("/budgets", body);
      setShowForm(false); await refresh();
    } catch (err: unknown) { setFormError((err as ApiError).message || "Save failed."); } finally { setSaving(false); }
  };
  const handleDelete = async (b: Budget) => {
    if (!confirm("Delete this budget?")) return;
    try { await api.delete(`/budgets/${b.id}`); await refresh(); } catch (err: unknown) { alert((err as ApiError).message || "Delete failed."); }
  };

  const budgets = state.status === "success" ? state.budgets : [];
  const totalAllocated = budgets.reduce((sum, b) => { const n = toNumberSafely(b.amount); return sum + (n === null ? 0 : n); }, 0);

  return (
    <div className="space-y-8">
      <PageHeader title="Budgets" description="Set and monitor budgets across your spending categories."
        actions={<div className="flex items-center gap-2">
          <Button variant="secondary" onClick={refresh} disabled={refreshing || state.status === "loading"} title="Refresh budgets"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />Refresh</Button>
          <Button onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Create Budget</Button>
        </div>} />

      {showForm && (
        <Card className="border-accent-500/25">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-foreground">{editing ? "Edit Budget" : "New Budget"}</h3><Button variant="ghost" size="sm" onClick={() => setShowForm(false)}><X className="h-4 w-4" /></Button></div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-1"><span className="text-xs text-muted">Category</span>
              <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm">
                <option value="">All categories</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <label className="space-y-1"><span className="text-xs text-muted">Amount *</span><Input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="5000" /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Period</span>
              <select value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value as BudgetPeriod })} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm">
                <option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option>
              </select>
            </label>
            <label className="space-y-1"><span className="text-xs text-muted">Start Date *</span><Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
            <label className="space-y-1"><span className="text-xs text-muted">End Date *</span><Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></label>
          </div>
          {isBusinessScope && <p className="mt-2 text-xs text-muted-faint">Will be created in the selected business.</p>}
          {formError && <p className="mt-3 flex items-center gap-1.5 text-sm text-danger-400"><Info className="h-4 w-4" />{formError}</p>}
          <div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => setShowForm(false)} disabled={saving}>Cancel</Button><Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{editing ? "Update" : "Create"}</Button></div>
        </Card>
      )}

      <section aria-label="Budgets summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Active Budgets" icon={PiggyBank} value={state.status === "success" ? budgets.length : "—"} hint="Budgets currently in effect" />
        <StatCard label="Allocated" icon={Gauge} value={state.status === "success" ? formatCurrency(totalAllocated) : "—"} hint="Total budgeted amount" />
      </section>

      <section aria-labelledby="budgets-list-heading">
        <SectionHeading id="budgets-list-heading" title="Your Budgets" description="Each budget tracks a category, amount, period, and spending progress." />
        {state.status === "loading" && <Card className="mt-4 flex items-center gap-3 p-6"><Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" /><p className="text-sm text-muted">Loading your budgets…</p></Card>}
        {state.status === "error" && <div className="mt-4"><EmptyState icon={PiggyBank} title="Could not load budgets" description={state.message} action={<Button variant="secondary" size="sm" onClick={load}><RotateCcw className="h-4 w-4" aria-hidden="true" />Retry</Button>} /></div>}
        {state.status === "success" && budgets.length === 0 && <Card className="mt-4"><EmptyState icon={PiggyBank} title="No budgets yet" description="Create your first budget to get started." action={<Button variant="secondary" size="sm" onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Create your first budget</Button>} /></Card>}
        {state.status === "success" && budgets.length > 0 && <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{budgets.map((b) => <BudgetCard key={b.id} budget={b} categoryName={b.category_id ? categoriesMap.get(b.category_id) : undefined} onEdit={() => openEdit(b)} onDelete={() => handleDelete(b)} />)}</div>}
      </section>

      <section aria-labelledby="budget-periods-heading">
        <SectionHeading id="budget-periods-heading" title="Budget Periods & Health" description="Budgets are evaluated over weekly, monthly, or yearly periods, and graded against actual spending." />
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card><div className="flex items-center gap-2"><CalendarRange className="h-4 w-4 text-accent-400" aria-hidden="true" /><h3 className="text-sm font-medium text-foreground">Periods</h3></div><div className="mt-3 flex flex-wrap gap-2">{(Object.keys(budgetPeriodLabels) as Array<keyof typeof budgetPeriodLabels>).map((p) => <Badge key={p} tone="neutral">{budgetPeriodLabels[p]}</Badge>)}</div></Card>
          <Card><div className="flex items-center gap-2"><Gauge className="h-4 w-4 text-accent-400" aria-hidden="true" /><h3 className="text-sm font-medium text-foreground">Health status</h3></div><div className="mt-3 flex flex-wrap gap-2">{STATUS_LEGEND.map((s) => <Badge key={s.key} tone={budgetStatusTones[s.key]}>{s.label}</Badge>)}</div><p className="mt-3 text-xs leading-relaxed text-muted-faint">Status is derived from progress: on track (&lt;80%), near limit (80–100%), or over (100%+).</p></Card>
        </div>
      </section>
    </div>
  );
}
