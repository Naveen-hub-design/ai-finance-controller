import { useCallback, useEffect, useRef, useState } from "react";
import { Tags, Plus, TrendingUp, TrendingDown, Info, Loader2, RotateCcw, RefreshCw, Pencil, Trash2, X } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { useAuth } from "../context/AuthContext";
import { api, type ApiError } from "../lib/api";
import type { Category, CategoriesResponse, CategoryType } from "../lib/types";

type LoadState = { status: "loading" } | { status: "success"; categories: Category[] } | { status: "error"; message: string };

function CategoryGroup({ title, badgeTone, description, icon: Icon, categories, onEdit, onDelete }: { title: string; badgeTone: "success" | "danger"; description: string; icon: typeof TrendingUp; categories: Category[]; onEdit: (c: Category) => void; onDelete: (c: Category) => void; }) {
  const isIncome = badgeTone === "success";
  return (
    <Card className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-raised text-accent-400"><Icon className="h-5 w-5" aria-hidden="true" /></div>
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          {categories.length > 0 && <span className="text-sm font-semibold tabular-nums text-foreground">{categories.length}</span>}
          <Badge tone={badgeTone}>{isIncome ? "Income" : "Expense"}</Badge>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted">{description}</p>
      {categories.length > 0 ? (
        <div className="mt-4 flex flex-1 flex-wrap content-start gap-2">
          {categories.map((c) => (
            <span key={c.id} className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-raised px-2.5 py-1 text-xs">
              {c.name}
              <button onClick={() => onEdit(c)} className="ml-1 text-muted hover:text-foreground"><Pencil className="h-3 w-3" /></button>
              <button onClick={() => onDelete(c)} className="text-muted hover:text-danger-400"><Trash2 className="h-3 w-3" /></button>
            </span>
          ))}
        </div>
      ) : (
        <div className="mt-4 flex-1"><EmptyState icon={isIncome ? TrendingUp : TrendingDown} title={`No ${title.toLowerCase()} categories`} description="Categories you create will be grouped here by type." /></div>
      )}
    </Card>
  );
}

export default function CategoriesPage() {
  const { user } = useAuth();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);
  const [form, setForm] = useState({ name: "", category_type: "expense" as CategoryType });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) { setState({ status: "error", message: "You must be signed in to view your categories." }); return; }
    cancelledRef.current = false;
    setState((prev) => (prev.status === "success" ? prev : { status: "loading" as const }));
    try {
      const res = await api.get<CategoriesResponse>(`/users/${user.id}/categories`);
      if (cancelledRef.current) return;
      setState({ status: "success", categories: res.categories ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      const msg = e.status === 403 ? "Access denied." : e.message || "Unable to load your categories.";
      setState({ status: "error", message: msg });
    }
  }, [user]);

  useEffect(() => { load(); return () => { cancelledRef.current = true; }; }, [load]);

  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const res = await api.get<CategoriesResponse>(`/users/${user.id}/categories`);
      if (cancelledRef.current) return;
      setState({ status: "success", categories: res.categories ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({ status: "error", message: e.message || "Unable to refresh your categories." });
    } finally { if (!cancelledRef.current) setRefreshing(false); }
  }, [user]);

  const openCreate = () => { setEditing(null); setForm({ name: "", category_type: "expense" }); setFormError(null); setShowForm(true); };
  const openEdit = (c: Category) => { setEditing(c); setForm({ name: c.name, category_type: c.category_type }); setFormError(null); setShowForm(true); };
  const handleSave = async () => {
    if (!form.name.trim()) { setFormError("Name is required."); return; }
    setSaving(true); setFormError(null);
    try {
      if (editing) await api.put(`/categories/${editing.id}`, { name: form.name.trim(), category_type: form.category_type });
      else await api.post("/categories", { name: form.name.trim(), category_type: form.category_type });
      setShowForm(false); await refresh();
    } catch (err: unknown) { setFormError((err as ApiError).message || "Save failed."); } finally { setSaving(false); }
  };
  const handleDelete = async (c: Category) => {
    if (!confirm(`Delete category "${c.name}"?`)) return;
    try { await api.delete(`/categories/${c.id}`); await refresh(); } catch (err: unknown) { alert((err as ApiError).message || "Delete failed."); }
  };

  const categories = state.status === "success" ? state.categories : [];
  const incomeCategories = categories.filter((c) => c.category_type === "income");
  const expenseCategories = categories.filter((c) => c.category_type === "expense");

  return (
    <div className="space-y-8">
      <PageHeader title="Categories" description="Organize your spending and income into categories for clearer analysis."
        actions={<div className="flex items-center gap-2">
          <Button variant="secondary" onClick={refresh} disabled={refreshing || state.status === "loading"} title="Refresh categories"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />Refresh</Button>
          <Button onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Add Category</Button>
        </div>} />

      {showForm && (
        <Card className="border-accent-500/25">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-foreground">{editing ? "Edit Category" : "New Category"}</h3><Button variant="ghost" size="sm" onClick={() => setShowForm(false)}><X className="h-4 w-4" /></Button></div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-1"><span className="text-xs text-muted">Name *</span><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Groceries" /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Type</span>
              <select value={form.category_type} onChange={(e) => setForm({ ...form, category_type: e.target.value as CategoryType })} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm">
                <option value="expense">Expense</option><option value="income">Income</option>
              </select>
            </label>
          </div>
          {formError && <p className="mt-3 flex items-center gap-1.5 text-sm text-danger-400"><Info className="h-4 w-4" />{formError}</p>}
          <div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => setShowForm(false)} disabled={saving}>Cancel</Button><Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{editing ? "Update" : "Create"}</Button></div>
        </Card>
      )}

      {state.status === "loading" && <Card className="flex items-center gap-3 p-6"><Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" /><p className="text-sm text-muted">Loading your categories…</p></Card>}
      {state.status === "error" && <EmptyState icon={Tags} title="Could not load categories" description={state.message} action={<Button variant="secondary" size="sm" onClick={load}><RotateCcw className="h-4 w-4" aria-hidden="true" />Retry</Button>} />}
      {state.status === "success" && (
        <>
          <section aria-labelledby="categories-overview-heading">
            <SectionHeading id="categories-overview-heading" title="Category Overview" description="Income and expense categories used to organize your transactions." />
            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <CategoryGroup title="Income" badgeTone="success" description="Sources of money coming into your finances." icon={TrendingUp} categories={incomeCategories} onEdit={openEdit} onDelete={handleDelete} />
              <CategoryGroup title="Expense" badgeTone="danger" description="Spending categories your expenses are grouped into." icon={TrendingDown} categories={expenseCategories} onEdit={openEdit} onDelete={handleDelete} />
            </div>
          </section>
          <section aria-labelledby="available-categories-heading">
            <SectionHeading id="available-categories-heading" title="All Categories" description="Every category, labeled by its type." action={categories.length > 0 ? <span className="text-sm text-muted">{categories.length} total</span> : undefined} />
            <Card className="mt-4">
              {categories.length === 0 ? <EmptyState icon={Tags} title="No categories yet" description="When categories are set up, they will be listed here." action={<Button variant="secondary" size="sm" onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Create a category</Button>} /> : (
                <div className="flex flex-wrap gap-2">{categories.map((c) => <Badge key={c.id} tone={c.category_type === "income" ? "success" : "danger"}>{c.name}</Badge>)}</div>
              )}
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
