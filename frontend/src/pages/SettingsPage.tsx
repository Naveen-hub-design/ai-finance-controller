import { useEffect, useState } from "react";
import {
  Save,
  CheckCircle2,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { SectionHeading } from "../components/ui/SectionHeading";
import { api, type ApiError } from "../lib/api";
import { getDisplayCurrency, setDisplayCurrency } from "../lib/format";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";

const ROLE_LABELS: Record<string, string> = {
  PLATFORM_ADMIN: "Platform Admin",
  MERCHANT: "Merchant",
  FINANCE_MANAGER: "Finance Manager",
};

interface HealthState {
  status: "checking" | "healthy" | "unavailable";
  detail?: string;
}

type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "saved" }
  | { status: "error"; message: string };

const selectClass =
  "h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-foreground transition-colors duration-150 hover:border-border-strong focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none";

export default function SettingsPage() {
  const { user, updateProfile } = useAuth();
  const {
    businesses,
    selectedBusiness,
    selectedBusinessId,
    selectBusiness,
    isLoading: businessesLoading,
  } = useBusiness();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [currency, setCurrency] = useState(getDisplayCurrency());
  const [saveState, setSaveState] = useState<SaveState>({ status: "idle" });
  const [health, setHealth] = useState<HealthState>({ status: "checking" });

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setEmail(user?.email ?? "");
  }, [user?.full_name, user?.email]);

  const checkHealth = () => {
    setHealth({ status: "checking" });
    api
      .get<{ status: string; service: string }>("/health")
      .then((res) => {
        setHealth({
          status: res.status === "healthy" ? "healthy" : "unavailable",
          detail: res.status,
        });
      })
      .catch((err: unknown) => {
        setHealth({
          status: "unavailable",
          detail: (err as ApiError).message,
        });
      });
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const handleSave = async () => {
    if (!user || saveState.status === "saving") return;
    setSaveState({ status: "saving" });
    try {
      await updateProfile({
        email: email.trim(),
        full_name: fullName.trim() || null,
      });
      setSaveState({ status: "saved" });
      window.setTimeout(
        () => setSaveState((s) => (s.status === "saved" ? { status: "idle" } : s)),
        2500
      );
    } catch (err: unknown) {
      const e = err as ApiError;
      setSaveState({
        status: "error",
        message: e.message || "Unable to save your profile.",
      });
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Application and account preferences."
      />

      <section aria-labelledby="profile-section">
        <SectionHeading
          id="profile-section"
          title="Profile"
          description="Your account information."
        />
        <Card className="mt-4 p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="full-name"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Full name
              </label>
              <Input
                id="full-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
            </div>
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Email
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
          </div>
          <p className="mt-4 text-xs text-muted-faint">
            Your name and email are saved to your account immediately.
          </p>
        </Card>
      </section>

      <section aria-labelledby="preferences-section">
        <SectionHeading
          id="preferences-section"
          title="Preferences"
          description="How the app formats and presents your finances."
        />
        <Card className="mt-4 p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="currency"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Display currency
              </label>
              <select
                id="currency"
                className={selectClass}
                value={currency}
                onChange={(e) => {
                  setCurrency(e.target.value);
                  setDisplayCurrency(e.target.value);
                }}
              >
                <option value="INR">INR — Indian Rupee</option>
                <option value="USD">USD — US Dollar</option>
                <option value="EUR">EUR — Euro</option>
                <option value="GBP">GBP — British Pound</option>
              </select>
            </div>
            <div>
              <label
                htmlFor="date-format"
                className="mb-1.5 block text-sm font-medium text-muted"
              >
                Date format
              </label>
              <select id="date-format" className={selectClass} defaultValue="dmy">
                <option value="dmy">DD Mon YYYY</option>
                <option value="mdy">Mon DD, YYYY</option>
              </select>
            </div>
          </div>
          <p className="mt-4 text-xs text-muted-faint">
            The display currency applies to every amount shown in the app and is
            saved on this device. The date format preference is stored but not
            yet reflected across the app.
          </p>
        </Card>
      </section>

      <section aria-labelledby="app-section">
        <SectionHeading
          id="app-section"
          title="Application"
          description="Version and service status."
        />
        <Card className="mt-4 p-5">
          <dl className="divide-y divide-border">
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-muted">Product</dt>
              <dd className="text-sm font-medium text-foreground">
                AI Finance Controller
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-muted">API status</dt>
              <dd className="flex items-center gap-2 text-sm font-medium">
                {health.status === "checking" && (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-accent-400" aria-hidden="true" />
                    <span className="text-foreground">Checking…</span>
                  </>
                )}
                {health.status === "healthy" && (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-success-500" aria-hidden="true" />
                    <span className="text-foreground">API healthy</span>
                    <button
                      type="button"
                      onClick={checkHealth}
                      aria-label="Re-check API status"
                      className="text-muted transition-colors hover:text-foreground"
                    >
                      <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </>
                )}
                {health.status === "unavailable" && (
                  <>
                    <AlertCircle className="h-4 w-4 text-danger-400" aria-hidden="true" />
                    <span className="text-danger-400">API unavailable</span>
                    <button
                      type="button"
                      onClick={checkHealth}
                      aria-label="Re-check API status"
                      className="text-muted transition-colors hover:text-foreground"
                    >
                      <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </>
                )}
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-muted">Authentication</dt>
              <dd className="text-sm font-medium text-foreground">
                {user?.email ?? "Signed in"}
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-muted">Role</dt>
              <dd className="text-sm font-medium text-foreground">
                <Badge tone={user?.role === "PLATFORM_ADMIN" ? "accent" : user?.role === "FINANCE_MANAGER" ? "warning" : "neutral"}>
                  {ROLE_LABELS[user?.role ?? ""] ?? user?.role ?? "Merchant"}
                </Badge>
              </dd>
            </div>
          </dl>
        </Card>
      </section>

      <section aria-labelledby="business-section">
        <SectionHeading
          id="business-section"
          title="Business & Memberships"
          description="The businesses you belong to and the current active scope."
        />
        <Card className="mt-4 p-5">
          {user?.role === "PLATFORM_ADMIN" ? (
            <p className="text-sm text-muted">
              Platform administrators operate at the platform level and do not
              belong to a specific business.
            </p>
          ) : businessesLoading ? (
            <p className="text-sm text-muted">Loading your businesses…</p>
          ) : businesses.length === 0 ? (
            <EmptyState
              title="No businesses yet"
              description="Businesses you join or create will appear here so you can manage their finances."
            />
          ) : (
            <div className="space-y-4">
              <div>
                <p className="mb-1.5 text-sm font-medium text-muted">
                  Active scope
                </p>
                <select
                  aria-label="Active business scope"
                  className={selectClass}
                  value={selectedBusinessId ?? ""}
                  onChange={(e) => selectBusiness(e.target.value || null)}
                >
                  <option value="">Personal Account</option>
                  {businesses.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} — {b.my_role === "OWNER" ? "Owner" : "Finance Manager"}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <p className="mb-1.5 text-sm font-medium text-muted">
                  Current
                </p>
                <p className="text-sm text-foreground">
                  {selectedBusiness
                    ? `${selectedBusiness.name} (${selectedBusiness.my_role === "OWNER" ? "Owner" : "Finance Manager"})`
                    : "Personal Account"}
                </p>
              </div>

              <div>
                <p className="mb-1.5 text-sm font-medium text-muted">
                  Memberships
                </p>
                <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {businesses.map((b) => (
                    <li
                      key={b.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
                    >
                      <span className="text-sm text-foreground">{b.name}</span>
                      <Badge tone={b.my_role === "OWNER" ? "accent" : "neutral"}>
                        {b.my_role === "OWNER" ? "Owner" : "Finance Manager"}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>
      </section>

      <div className="flex items-center gap-3">
        <Button
          onClick={handleSave}
          disabled={!user || saveState.status === "saving"}
        >
          {saveState.status === "saving" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Save className="h-4 w-4" aria-hidden="true" />
          )}
          {saveState.status === "saving" ? "Saving…" : "Save changes"}
        </Button>
        {saveState.status === "saved" && (
          <span className="flex items-center gap-1.5 text-sm text-success-500">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            Saved
          </span>
        )}
        {saveState.status === "error" && (
          <span className="flex items-center gap-1.5 text-sm text-danger-400">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            {saveState.message}
          </span>
        )}
      </div>
    </div>
  );
}
