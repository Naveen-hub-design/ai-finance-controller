import { useCallback, useEffect, useRef, useState } from "react";
import {
  Wallet,
  Plus,
  Landmark,
  CircleDollarSign,
  Info,
  Loader2,
  RotateCcw,
  RefreshCw,
  Hash,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { StatCard } from "../components/ui/StatCard";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { accountTypeLabels } from "../lib/labels";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type { Account, AccountsResponse, AccountType } from "../lib/types";
import { formatCurrency } from "../lib/format";

type LoadState =
  | { status: "loading" }
  | { status: "success"; accounts: Account[] }
  | { status: "error"; message: string };

function AccountRow({
  account,
  onEdit,
  onDelete,
}: {
  account: Account;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="grid grid-cols-1 items-center gap-3 px-5 py-4 sm:grid-cols-[1fr_auto_auto_auto] sm:gap-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
          <Wallet className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{account.name}</p>
          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-faint">
            <Hash className="h-3 w-3" aria-hidden="true" />
            {account.id.slice(0, 8)}…
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 sm:justify-end">
        <Badge tone="neutral">{accountTypeLabels[account.account_type]}</Badge>
        <Badge tone="accent">{account.currency}</Badge>
      </div>
      <p className="text-right text-base font-semibold tabular-nums tracking-tight text-foreground">
        {formatCurrency(account.current_balance, account.currency)}
      </p>
      <div className="flex items-center justify-end gap-1">
        <Button variant="ghost" size="sm" onClick={onEdit} title="Edit account">
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="sm" onClick={onDelete} title="Delete account">
          <Trash2 className="h-3.5 w-3.5 text-danger-400" />
        </Button>
      </div>
    </div>
  );
}

export default function AccountsPage() {
  const { user } = useAuth();
  const { businessQuery, selectedBusinessId, isBusinessScope } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState({ name: "", account_type: "bank" as AccountType, currency: "INR", current_balance: "0" });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) { setState({ status: "error", message: "You must be signed in to view your accounts." }); return; }
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const res = await api.get<AccountsResponse>(`/users/${user.id}/accounts${businessQuery()}`);
      if (cancelledRef.current) return;
      setState({ status: "success", accounts: res.accounts ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      const msg = e.status === 403 ? "Access denied for this business." : e.status === 404 ? "Not found." : e.message || "Unable to load your accounts.";
      setState({ status: "error", message: msg });
    }
  }, [user, businessQuery]);

  useEffect(() => { load(); return () => { cancelledRef.current = true; }; }, [load]);

  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const res = await api.get<AccountsResponse>(`/users/${user.id}/accounts${businessQuery()}`);
      if (cancelledRef.current) return;
      setState({ status: "success", accounts: res.accounts ?? [] });
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({ status: "error", message: e.message || "Unable to refresh your accounts." });
    } finally { if (!cancelledRef.current) setRefreshing(false); }
  }, [user, businessQuery]);

  const openCreate = () => { setEditing(null); setForm({ name: "", account_type: "bank", currency: "INR", current_balance: "0" }); setFormError(null); setShowForm(true); };
  const openEdit = (a: Account) => { setEditing(a); setForm({ name: a.name, account_type: a.account_type, currency: a.currency, current_balance: a.current_balance }); setFormError(null); setShowForm(true); };

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError("Name is required."); return; }
    const bal = Number(form.current_balance);
    if (!Number.isFinite(bal)) { setFormError("Balance must be a number."); return; }
    setSaving(true); setFormError(null);
    try {
      if (editing) {
        await api.put(`/accounts/${editing.id}`, { name: form.name.trim(), account_type: form.account_type, currency: form.currency.trim().toUpperCase(), current_balance: String(bal) });
      } else {
        const body: Record<string, unknown> = { name: form.name.trim(), account_type: form.account_type, currency: form.currency.trim().toUpperCase(), current_balance: String(bal) };
        if (isBusinessScope && selectedBusinessId) body.business_id = selectedBusinessId;
        await api.post("/accounts", body);
      }
      setShowForm(false); await refresh();
    } catch (err: unknown) {
      const e = err as ApiError;
      setFormError(e.status === 403 ? "Not authorized for this business." : e.message || "Save failed.");
    } finally { setSaving(false); }
  };

  const handleDelete = async (a: Account) => {
    if (!confirm(`Delete account "${a.name}"?`)) return;
    try { await api.delete(`/accounts/${a.id}`); await refresh(); } catch (err: unknown) { alert((err as ApiError).message || "Delete failed."); }
  };

  const types = Object.keys(accountTypeLabels) as Array<keyof typeof accountTypeLabels>;
  const accounts = state.status === "success" ? state.accounts : [];
  const totalBalance = accounts.reduce((sum, a) => { const n = Number(a.current_balance); return sum + (Number.isFinite(n) ? n : 0); }, 0);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Accounts"
        description="All your linked accounts and their running balances at a glance."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={refresh} disabled={refreshing || state.status === "loading"} title="Refresh account data">
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
              Refresh
            </Button>
            <Button onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Add Account</Button>
          </div>
        }
      />

      {showForm && (
        <Card className="border-accent-500/25">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">{editing ? "Edit Account" : "New Account"}</h3>
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}><X className="h-4 w-4" /></Button>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-1"><span className="text-xs text-muted">Name *</span><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My Bank Account" /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Type</span>
              <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value as AccountType })} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm">
                {types.map((t) => <option key={t} value={t}>{accountTypeLabels[t]}</option>)}
              </select>
            </label>
            <label className="space-y-1"><span className="text-xs text-muted">Currency</span><Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} placeholder="INR" maxLength={3} /></label>
            <label className="space-y-1"><span className="text-xs text-muted">Balance</span><Input type="number" step="0.01" value={form.current_balance} onChange={(e) => setForm({ ...form, current_balance: e.target.value })} /></label>
          </div>
          {isBusinessScope && <p className="mt-2 text-xs text-muted-faint">Will be created in the selected business.</p>}
          {formError && <p className="mt-3 flex items-center gap-1.5 text-sm text-danger-400"><Info className="h-4 w-4" />{formError}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowForm(false)} disabled={saving}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{editing ? "Update" : "Create"}</Button>
          </div>
        </Card>
      )}

      <section aria-label="Accounts summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Total Accounts" icon={Landmark} value={state.status === "success" ? accounts.length : "—"} hint="Number of linked accounts" />
        <StatCard label="Total Balance" icon={CircleDollarSign} value={state.status === "success" ? formatCurrency(totalBalance) : "—"} hint="Sum across all linked accounts" />
      </section>

      <section aria-labelledby="accounts-list-heading">
        <SectionHeading id="accounts-list-heading" title="Your Accounts" description="Linked accounts with their account type and running balance." />
        <Card className="mt-4 overflow-hidden p-0">
          {state.status === "loading" && <div className="flex items-center gap-3 p-6"><Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" /><p className="text-sm text-muted">Loading your accounts…</p></div>}
          {state.status === "error" && <div className="p-5"><EmptyState icon={Wallet} title="Could not load accounts" description={state.message} action={<Button variant="secondary" size="sm" onClick={load}><RotateCcw className="h-4 w-4" aria-hidden="true" />Retry</Button>} /></div>}
          {state.status === "success" && accounts.length === 0 && <div className="p-5"><EmptyState icon={Wallet} title="No accounts linked yet" description="Create your first account to get started." action={<Button variant="secondary" size="sm" onClick={openCreate}><Plus className="h-4 w-4" aria-hidden="true" />Add your first account</Button>} /></div>}
          {state.status === "success" && accounts.length > 0 && (
            <>
              <div className="hidden grid-cols-[1fr_auto_auto_auto] items-center gap-4 border-b border-border px-5 py-3 sm:grid">
                <span className="text-xs font-medium uppercase tracking-wide text-muted">Account</span>
                <span className="w-32 text-right text-xs font-medium uppercase tracking-wide text-muted">Type</span>
                <span className="w-32 text-right text-xs font-medium uppercase tracking-wide text-muted">Balance</span>
                <span className="w-20 text-right text-xs font-medium uppercase tracking-wide text-muted">Actions</span>
              </div>
              <div className="divide-y divide-border">{accounts.map((a) => <AccountRow key={a.id} account={a} onEdit={() => openEdit(a)} onDelete={() => handleDelete(a)} />)}</div>
            </>
          )}
        </Card>
      </section>

      <section aria-labelledby="account-types-heading">
        <SectionHeading id="account-types-heading" title="Account Types" description="Accounts are grouped by the type of financial instrument they represent." />
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {types.map((type) => <Card key={type} className="flex flex-col items-center justify-center gap-2 p-4 text-center"><Badge tone="neutral">{accountTypeLabels[type]}</Badge></Card>)}
        </div>
      </section>
    </div>
  );
}
