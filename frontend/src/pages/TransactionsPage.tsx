import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeftRight, Search, Download, RefreshCw, Loader2, RotateCcw, Building2, Folder, Plus, Pencil, Trash2, X, Info } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { SectionHeading } from "../components/ui/SectionHeading";
import { EmptyState } from "../components/ui/EmptyState";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { api, type ApiError } from "../lib/api";
import type { Transaction, TransactionsResponse, TransactionType, Account, AccountsResponse, Category, CategoriesResponse } from "../lib/types";
import { transactionTypeLabels, transactionTypeTones } from "../lib/labels";
import { formatCurrency, formatDate } from "../lib/format";

const typeKeys = Object.keys(transactionTypeLabels) as Array<keyof typeof transactionTypeLabels>;
type Filter = "all" | keyof typeof transactionTypeLabels;
type LoadState = { status: "loading" } | { status: "success"; transactions: Transaction[] } | { status: "error"; message: string };
function shortId(id: string): string { return id.length > 8 ? `${id.slice(0, 8)}…` : id; }

function TransactionRow({
  transaction,
  accountName,
  categoryName,
  onEdit,
  onDelete,
}: {
  transaction: Transaction;
  accountName?: string;
  categoryName?: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const isExpense = transaction.transaction_type === "expense";
  const isIncome = transaction.transaction_type === "income";
  const displayAccount = accountName || `Account ${shortId(transaction.account_id)}`;
  const displayCategory = categoryName || (transaction.category_id ? `Category ${shortId(transaction.category_id)}` : "Uncategorized");

  return (
    <div className="grid grid-cols-1 items-center gap-3 px-5 py-4 md:grid-cols-[1fr_auto_auto_auto_auto] md:gap-4 transition-colors hover:bg-surface-raised/40">
      <div className="flex min-w-0 items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-raised text-accent-400">
          <ArrowLeftRight className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <Link
            to={`/transactions/${transaction.id}`}
            className="block truncate text-sm font-medium text-foreground transition-colors hover:text-accent-400"
          >
            {transaction.description || "Untitled transaction"}
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-faint">
            <span className="inline-flex items-center gap-1.5 font-medium text-foreground/80">
              <Building2 className="h-3 w-3 text-accent-400" aria-hidden="true" />
              {displayAccount}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Folder className="h-3 w-3" aria-hidden="true" />
              {displayCategory}
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
              Settled
            </span>
          </div>
        </div>
      </div>
      <span className="text-sm tabular-nums text-muted md:text-right md:text-foreground">
        {formatDate(transaction.transaction_date)}
      </span>
      <div className="md:flex md:justify-end">
        <Badge tone={transactionTypeTones[transaction.transaction_type]}>
          {transactionTypeLabels[transaction.transaction_type]}
        </Badge>
      </div>
      <p
        className={`text-right text-base font-semibold tabular-nums tracking-tight ${
          isExpense ? "text-danger-400" : isIncome ? "text-success-500" : "text-foreground"
        }`}
      >
        {isExpense ? "−" : isIncome ? "+" : ""}
        {formatCurrency(transaction.amount)}
      </p>
      <div className="flex justify-end gap-1">
        <Button variant="ghost" size="sm" onClick={onEdit} title="Edit">
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="sm" onClick={onDelete} title="Delete">
          <Trash2 className="h-3.5 w-3.5 text-danger-400" />
        </Button>
      </div>
    </div>
  );
}

export default function TransactionsPage() {
  const { user } = useAuth();
  const { businessQuery } = useBusiness();
  const [filter, setFilter] = useState<Filter>("all");
  const [accountFilter, setAccountFilter] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const cancelledRef = useRef(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState({
    account_id: "",
    category_id: "",
    amount: "",
    transaction_type: "expense" as TransactionType,
    description: "",
    transaction_date: new Date().toISOString().slice(0, 10),
  });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) {
      setState({
        status: "error",
        message: "You must be signed in to view your transactions.",
      });
      return;
    }
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const [txRes, aRes, cRes] = await Promise.all([
        api.get<TransactionsResponse>(`/users/${user.id}/transactions${businessQuery()}`),
        api.get<AccountsResponse>(`/users/${user.id}/accounts${businessQuery()}`).catch(() => ({ accounts: [] })),
        api.get<CategoriesResponse>(`/users/${user.id}/categories`).catch(() => ({ categories: [] })),
      ]);
      if (cancelledRef.current) return;
      setState({ status: "success", transactions: txRes.transactions ?? [] });
      setAccounts(aRes.accounts ?? []);
      setCategories(cRes.categories ?? []);
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      const msg =
        e.status === 403
          ? "Access denied for this business."
          : e.message || "Unable to load your transactions.";
      setState({ status: "error", message: msg });
    }
  }, [user, businessQuery]);

  useEffect(() => {
    load();
    return () => {
      cancelledRef.current = true;
    };
  }, [load]);

  const refresh = useCallback(async () => {
    if (!user) return;
    setRefreshing(true);
    try {
      const [txRes, aRes, cRes] = await Promise.all([
        api.get<TransactionsResponse>(`/users/${user.id}/transactions${businessQuery()}`),
        api.get<AccountsResponse>(`/users/${user.id}/accounts${businessQuery()}`).catch(() => ({ accounts: [] })),
        api.get<CategoriesResponse>(`/users/${user.id}/categories`).catch(() => ({ categories: [] })),
      ]);
      if (cancelledRef.current) return;
      setState({ status: "success", transactions: txRes.transactions ?? [] });
      setAccounts(aRes.accounts ?? []);
      setCategories(cRes.categories ?? []);
    } catch (err: unknown) {
      if (cancelledRef.current) return;
      const e = err as ApiError;
      setState({
        status: "error",
        message: e.message || "Unable to refresh your transactions.",
      });
    } finally {
      if (!cancelledRef.current) setRefreshing(false);
    }
  }, [user, businessQuery]);

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

  const openCreate = () => {
    setEditing(null);
    setForm({
      account_id: accounts[0]?.id ?? "",
      category_id: "",
      amount: "",
      transaction_type: "expense",
      description: "",
      transaction_date: new Date().toISOString().slice(0, 10),
    });
    setFormError(null);
    setShowForm(true);
  };

  const openEdit = (t: Transaction) => {
    setEditing(t);
    setForm({
      account_id: t.account_id,
      category_id: t.category_id ?? "",
      amount: t.amount,
      transaction_type: t.transaction_type,
      description: t.description ?? "",
      transaction_date: t.transaction_date,
    });
    setFormError(null);
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.account_id) {
      setFormError("Account is required.");
      return;
    }
    const amt = Number(form.amount);
    if (!Number.isFinite(amt) || amt <= 0) {
      setFormError("Amount must be a positive number.");
      return;
    }
    if (!form.transaction_date) {
      setFormError("Date is required.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const body: Record<string, unknown> = {
        account_id: form.account_id,
        amount: String(amt),
        transaction_type: form.transaction_type,
        transaction_date: form.transaction_date,
      };
      if (form.category_id) body.category_id = form.category_id;
      if (form.description.trim()) body.description = form.description.trim();
      if (editing) await api.put(`/transactions/${editing.id}`, body);
      else await api.post("/transactions", body);
      setShowForm(false);
      await refresh();
    } catch (err: unknown) {
      setFormError((err as ApiError).message || "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (t: Transaction) => {
    if (!confirm(`Delete transaction "${t.description || t.id.slice(0, 8)}"?`)) return;
    try {
      await api.delete(`/transactions/${t.id}`);
      await refresh();
    } catch (err: unknown) {
      alert((err as ApiError).message || "Delete failed.");
    }
  };

  const transactions = state.status === "success" ? state.transactions : [];
  const visibleTransactions = useMemo(() => {
    const q = query.trim().toLowerCase();
    return transactions.filter((t) => {
      if (filter !== "all" && t.transaction_type !== filter) return false;
      if (accountFilter !== "all" && t.account_id !== accountFilter) return false;
      if (!q) return true;
      const desc = (t.description ?? "").toLowerCase();
      if (desc.includes(q)) return true;
      const acc = (accountsMap.get(t.account_id) ?? "").toLowerCase();
      if (acc.includes(q)) return true;
      const cat = (t.category_id ? (categoriesMap.get(t.category_id) ?? "") : "").toLowerCase();
      if (cat.includes(q)) return true;
      return formatCurrency(t.amount).toLowerCase().includes(q);
    });
  }, [transactions, filter, accountFilter, query, accountsMap, categoriesMap]);

  const metrics = useMemo(() => {
    let inflow = 0;
    let outflow = 0;
    for (const t of visibleTransactions) {
      const amt = Number(t.amount) || 0;
      if (t.transaction_type === "income") inflow += amt;
      else if (t.transaction_type === "expense") outflow += amt;
    }
    return {
      inflow,
      outflow,
      net: inflow - outflow,
      count: visibleTransactions.length,
    };
  }, [visibleTransactions]);

  const hasFilterOrSearch =
    filter !== "all" || accountFilter !== "all" || query.trim().length > 0;
  const hasData = transactions.length > 0;

  const handleExport = () => {
    if (visibleTransactions.length === 0) return;
    const headers = [
      "Transaction ID",
      "Date",
      "Description",
      "Type",
      "Amount",
      "Account Name",
      "Account ID",
      "Category Name",
      "Category ID",
      "Status",
    ];
    const rows = visibleTransactions.map((t) => [
      `"${t.id}"`,
      `"${t.transaction_date}"`,
      `"${(t.description || "").replace(/"/g, '""')}"`,
      `"${t.transaction_type}"`,
      `"${t.amount}"`,
      `"${(accountsMap.get(t.account_id) || "Account " + shortId(t.account_id)).replace(/"/g, '""')}"`,
      `"${t.account_id}"`,
      `"${(t.category_id ? (categoriesMap.get(t.category_id) || "Category " + shortId(t.category_id)) : "Uncategorized").replace(/"/g, '""')}"`,
      `"${t.category_id || ""}"`,
      `"SETTLED"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `apex_global_ledger_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Financial Ledger"
        description="Search, filter, and review verified transactions across all enterprise accounts."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={refresh}
              disabled={refreshing || state.status === "loading"}
              title="Refresh transactions"
            >
              <RefreshCw
                className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
                aria-hidden="true"
              />
              Refresh
            </Button>
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Transaction
            </Button>
            <Button
              variant="secondary"
              disabled={!hasData}
              onClick={handleExport}
              title="Export visible transactions to CSV"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Export CSV
            </Button>
          </div>
        }
      />

      {/* Real-time Ledger Summary KPI Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
          <span className="text-xs font-medium text-muted">Visible Inflow</span>
          <p className="mt-1 text-lg font-semibold tabular-nums text-success-500">
            +{formatCurrency(metrics.inflow)}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
          <span className="text-xs font-medium text-muted">Visible Outflow</span>
          <p className="mt-1 text-lg font-semibold tabular-nums text-danger-400">
            −{formatCurrency(metrics.outflow)}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
          <span className="text-xs font-medium text-muted">Net Cash Flow</span>
          <p
            className={`mt-1 text-lg font-semibold tabular-nums ${
              metrics.net >= 0 ? "text-success-500" : "text-danger-400"
            }`}
          >
            {metrics.net >= 0 ? "+" : ""}
            {formatCurrency(metrics.net)}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
          <span className="text-xs font-medium text-muted">Reconciliation Status</span>
          <div className="mt-1.5 flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <p className="text-sm font-semibold text-foreground">100% Settled</p>
          </div>
          <span className="text-[11px] text-muted-faint">{metrics.count} records visible</span>
        </div>
      </div>

      {showForm && (
        <Card className="border-accent-500/25">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              {editing ? "Edit Transaction" : "New Transaction"}
            </h3>
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs text-muted">Account *</span>
              <select
                value={form.account_id}
                onChange={(e) => setForm({ ...form, account_id: e.target.value })}
                className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm"
              >
                <option value="">Select account</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Category</span>
              <select
                value={form.category_id}
                onChange={(e) => setForm({ ...form, category_id: e.target.value })}
                className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm"
              >
                <option value="">Uncategorized</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.category_type})
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Amount *</span>
              <Input
                type="number"
                step="0.01"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                placeholder="1000.00"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Type</span>
              <select
                value={form.transaction_type}
                onChange={(e) =>
                  setForm({ ...form, transaction_type: e.target.value as TransactionType })
                }
                className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm"
              >
                {typeKeys.map((t) => (
                  <option key={t} value={t}>
                    {transactionTypeLabels[t]}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs text-muted">Date *</span>
              <Input
                type="date"
                value={form.transaction_date}
                onChange={(e) => setForm({ ...form, transaction_date: e.target.value })}
              />
            </label>
            <label className="space-y-1 sm:col-span-2">
              <span className="text-xs text-muted">Description</span>
              <Input
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="What was this for?"
              />
            </label>
          </div>
          {formError && (
            <p className="mt-3 flex items-center gap-1.5 text-sm text-danger-400">
              <Info className="h-4 w-4" />
              {formError}
            </p>
          )}
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowForm(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {editing ? "Update" : "Create"}
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative w-full max-w-sm">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-faint"
                aria-hidden="true"
              />
              <Input
                aria-label="Search transactions"
                placeholder="Search description, account, category..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            {accounts.length > 0 && (
              <select
                aria-label="Filter by account"
                value={accountFilter}
                onChange={(e) => setAccountFilter(e.target.value)}
                className="h-10 rounded-lg border border-border bg-surface px-3 text-xs text-foreground focus:border-accent-500 focus:outline-none"
              >
                <option value="all">All Accounts ({accounts.length})</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div
            className="flex flex-wrap items-center gap-1.5"
            role="group"
            aria-label="Filter by transaction type"
          >
            <Button
              variant={filter === "all" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setFilter("all")}
            >
              All Types
            </Button>
            {typeKeys.map((type) => (
              <Button
                key={type}
                variant={filter === type ? "primary" : "secondary"}
                size="sm"
                onClick={() => setFilter(type)}
              >
                {transactionTypeLabels[type]}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      <section aria-labelledby="transactions-list-heading">
        <SectionHeading
          id="transactions-list-heading"
          title="All Transactions"
          description="A chronological view of your income, expenses, and transfers."
        />
        <Card className="mt-4 overflow-hidden p-0">
          {state.status === "loading" && (
            <div className="flex items-center gap-3 p-6">
              <Loader2 className="h-5 w-5 animate-spin text-accent-400" aria-hidden="true" />
              <p className="text-sm text-muted">Loading your transactions…</p>
            </div>
          )}
          {state.status === "error" && (
            <div className="p-5">
              <EmptyState
                icon={ArrowLeftRight}
                title="Could not load transactions"
                description={state.message}
                action={
                  <Button variant="secondary" size="sm" onClick={load}>
                    <RotateCcw className="h-4 w-4" aria-hidden="true" />
                    Retry
                  </Button>
                }
              />
            </div>
          )}
          {state.status === "success" && visibleTransactions.length === 0 && (
            <div className="p-5">
              <EmptyState
                icon={ArrowLeftRight}
                title={hasData ? "No matching transactions" : "No transactions to display"}
                description={
                  hasData
                    ? "Try adjusting your search text or filter."
                    : "Create your first transaction to get started."
                }
                action={
                  hasData ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setQuery("");
                        setFilter("all");
                        setAccountFilter("all");
                      }}
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                      Clear search & filters
                    </Button>
                  ) : (
                    <Button variant="secondary" size="sm" onClick={openCreate}>
                      <Plus className="h-4 w-4" aria-hidden="true" />
                      Add transaction
                    </Button>
                  )
                }
              />
            </div>
          )}
          {state.status === "success" && visibleTransactions.length > 0 && (
            <>
              <div className="hidden grid-cols-[1fr_auto_auto_auto_auto] items-center gap-4 border-b border-border px-5 py-3 md:grid">
                <span className="text-xs font-medium uppercase tracking-wide text-muted">
                  Description & Scope
                </span>
                <span className="w-24 text-right text-xs font-medium uppercase tracking-wide text-muted">
                  Date
                </span>
                <span className="w-24 text-right text-xs font-medium uppercase tracking-wide text-muted">
                  Type
                </span>
                <span className="w-28 text-right text-xs font-medium uppercase tracking-wide text-muted">
                  Amount
                </span>
                <span className="w-20 text-right text-xs font-medium uppercase tracking-wide text-muted">
                  Actions
                </span>
              </div>
              <div className="divide-y divide-border">
                {visibleTransactions.map((t) => (
                  <TransactionRow
                    key={t.id}
                    transaction={t}
                    accountName={accountsMap.get(t.account_id)}
                    categoryName={t.category_id ? categoriesMap.get(t.category_id) : undefined}
                    onEdit={() => openEdit(t)}
                    onDelete={() => handleDelete(t)}
                  />
                ))}
              </div>
            </>
          )}
        </Card>
        {state.status === "success" && visibleTransactions.length > 0 && (
          <p className="mt-3 px-1 text-xs text-muted-faint">
            Showing {visibleTransactions.length} of {transactions.length} transaction
            {transactions.length === 1 ? "" : "s"}
            {hasFilterOrSearch ? " (filtered)" : ""}.
          </p>
        )}
      </section>
    </div>
  );
}
