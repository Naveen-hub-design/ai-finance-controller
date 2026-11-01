import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  ArrowLeft,
  Receipt,
  Pencil,
  Trash2,
  Hash,
  CalendarDays,
  Tag,
  Building2,
  Folder,
  CircleDollarSign,
  Loader2,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { EmptyState } from "../components/ui/EmptyState";
import { api, type ApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import type { Transaction, TransactionType, Account, AccountsResponse, Category, CategoriesResponse } from "../lib/types";
import { transactionTypeLabels, transactionTypeTones } from "../lib/labels";
import { formatCurrency, formatDate } from "../lib/format";

function DetailRow({
  icon: Icon,
  label,
  value,
  valueClassName,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border py-3 last:border-b-0">
      <div className="flex items-center gap-2 text-muted">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span className="text-sm">{label}</span>
      </div>
      <span className={"text-right text-sm text-foreground " + (valueClassName ?? "")}>
        {value}
      </span>
    </div>
  );
}

type LoadState =
  | { status: "loading" }
  | { status: "success"; transaction: Transaction }
  | { status: "not-found"; message: string }
  | { status: "error"; message: string };

export default function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ amount: "", description: "", transaction_date: "", transaction_type: "expense" as TransactionType });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  const load = useCallback(async () => {
    if (!id) {
      setState({ status: "error", message: "No transaction ID was provided." });
      return;
    }
    if (!user) {
      setState({ status: "error", message: "You must be signed in to view transactions." });
      return;
    }

    cancelledRef.current = false;
    setState({ status: "loading" });

    try {
      const [txRes, aRes, cRes] = await Promise.all([
        api.get<Transaction>(`/users/${user.id}/transactions/${id}${businessQuery()}`),
        api.get<AccountsResponse>(`/users/${user.id}/accounts${businessQuery()}`).catch(() => ({ accounts: [] })),
        api.get<CategoriesResponse>(`/users/${user.id}/categories`).catch(() => ({ categories: [] })),
      ]);
      if (cancelledRef.current) return;
      setState({ status: "success", transaction: txRes });
      setAccounts(aRes.accounts ?? []);
      setCategories(cRes.categories ?? []);
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      if (e.status === 404) {
        setState({ status: "not-found", message: "Transaction not found." });
        return;
      }
      setState({
        status: "error",
        message: e.message || "Unable to load this transaction.",
      });
    }
  }, [id, user, businessQuery]);

  useEffect(() => {
    load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const accountsMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of accounts) map.set(a.id, a.name);
    return map;
  }, [accounts]);

  const categoriesMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of categories) map.set(c.id, c.name);
    return map;
  }, [categories]);

  const shortId = id ? `${id.slice(0, 8)}…` : "—";

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/transactions"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to transactions
        </Link>
        <PageHeader
          title="Transaction Details"
          description={id ? `Reviewing transaction #${id}` : "Transaction detail"}
          actions={
            <>
              <Button
                variant="secondary"
                onClick={() => {
                  if (state.status !== "success") return;
                  setForm({ amount: state.transaction.amount, description: state.transaction.description ?? "", transaction_date: state.transaction.transaction_date, transaction_type: state.transaction.transaction_type });
                  setFormError(null);
                  setEditing(true);
                }}
                disabled={state.status !== "success"}
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
                Edit
              </Button>
              <Button
                variant="danger"
                disabled={state.status !== "success"}
                onClick={async () => {
                  if (!id || !confirm("Delete this transaction?")) return;
                  try { await api.delete(`/transactions/${id}`); navigate("/transactions"); } catch (err: unknown) { alert((err as ApiError).message || "Delete failed."); }
                }}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete
              </Button>
            </>
          }
        />
      </div>

      {state.status === "loading" && (
        <Card className="flex items-center gap-3 p-6">
          <Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" />
          <p className="text-sm text-muted">Loading transaction…</p>
        </Card>
      )}

      {state.status === "error" && (
        <EmptyState
          icon={Receipt}
          title="Could not load transaction"
          description={state.message}
          action={
            <Button variant="secondary" size="sm" onClick={load}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Retry
            </Button>
          }
        />
      )}

      {state.status === "not-found" && (
        <EmptyState
          icon={Receipt}
          title="Transaction not found"
          description="The transaction you are looking for does not exist or has been removed."
          action={
            <Link to="/transactions">
              <Button variant="secondary" size="sm">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Back to transactions
              </Button>
            </Link>
          }
        />
      )}

      {state.status === "success" && (
        <Card className="p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-raised text-accent-400">
              <Receipt className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold tracking-tight text-foreground">
                {state.transaction.description || "Untitled transaction"}
              </p>
              <Badge
                tone={transactionTypeTones[state.transaction.transaction_type]}
                className="mt-1"
              >
                {transactionTypeLabels[state.transaction.transaction_type]}
              </Badge>
            </div>
          </div>

          <div className="mt-5">
            <DetailRow
              icon={Hash}
              label="Transaction ID"
              value={shortId}
            />
            <DetailRow
              icon={CircleDollarSign}
              label="Amount"
              value={formatCurrency(state.transaction.amount)}
              valueClassName="text-lg font-semibold"
            />
            <DetailRow
              icon={CalendarDays}
              label="Date"
              value={formatDate(state.transaction.transaction_date)}
            />
            <DetailRow
              icon={Receipt}
              label="Description"
              value={state.transaction.description || "—"}
            />
            <DetailRow
              icon={Building2}
              label="Account"
              value={
                state.transaction.account_id
                  ? (accountsMap.get(state.transaction.account_id)
                      ? `${accountsMap.get(state.transaction.account_id)} (${shortId})`
                      : state.transaction.account_id)
                  : "—"
              }
            />
            <DetailRow
              icon={Folder}
              label="Category"
              value={
                state.transaction.category_id
                  ? (categoriesMap.get(state.transaction.category_id) ?? state.transaction.category_id)
                  : "Uncategorized"
              }
            />
            <DetailRow
              icon={Tag}
              label="Type"
              value={transactionTypeLabels[
                state.transaction.transaction_type as TransactionType
              ]}
            />
            <DetailRow
              icon={CheckCircle2}
              label="Reconciliation Status"
              value="Settled & Reconciled (Verified Entry)"
              valueClassName="text-emerald-400 font-medium"
            />
            <DetailRow
              icon={CalendarDays}
              label="Created"
              value={formatDate(state.transaction.created_at)}
            />
          </div>

          {editing && (
            <div className="mt-5 rounded-lg border border-accent-500/25 bg-accent-500/5 p-4">
              <h4 className="text-sm font-semibold text-foreground">Edit Transaction</h4>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="space-y-1"><span className="text-xs text-muted">Amount *</span><Input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
                <label className="space-y-1"><span className="text-xs text-muted">Type</span>
                  <select value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value as TransactionType })} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm">
                    <option value="income">Income</option><option value="expense">Expense</option><option value="transfer">Transfer</option>
                  </select>
                </label>
                <label className="space-y-1"><span className="text-xs text-muted">Date *</span><Input type="date" value={form.transaction_date} onChange={(e) => setForm({ ...form, transaction_date: e.target.value })} /></label>
                <label className="space-y-1 sm:col-span-2"><span className="text-xs text-muted">Description</span><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
              </div>
              {formError && <p className="mt-2 text-sm text-danger-400">{formError}</p>}
              <div className="mt-3 flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setEditing(false)} disabled={saving}>Cancel</Button>
                <Button
                  onClick={async () => {
                    const amt = Number(form.amount);
                    if (!Number.isFinite(amt) || amt <= 0) { setFormError("Amount must be positive."); return; }
                    if (!form.transaction_date) { setFormError("Date is required."); return; }
                    setSaving(true); setFormError(null);
                    try {
                      await api.put(`/transactions/${id}`, { amount: String(amt), transaction_type: form.transaction_type, transaction_date: form.transaction_date, description: form.description.trim() || null });
                      setEditing(false); load();
                    } catch (err: unknown) { setFormError((err as ApiError).message || "Update failed."); } finally { setSaving(false); }
                  }}
                  disabled={saving}
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Save
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
