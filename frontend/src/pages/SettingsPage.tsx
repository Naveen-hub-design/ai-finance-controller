import { useState } from "react";
import { Save, CheckCircle2 } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { SectionHeading } from "../components/ui/SectionHeading";
import { useAuth } from "../context/AuthContext";

const selectClass =
  "h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-foreground transition-colors duration-150 focus:border-accent-500 focus:outline-none";

export default function SettingsPage() {
  const { user } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Application and account preferences."
      />

      <section aria-labelledby="profile-section">
        <SectionHeading
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
            Profile updates are not submitted yet. Saving your details will be
            connected to the users API in a later milestone (after
            authentication).
          </p>
        </Card>
      </section>

      <section aria-labelledby="preferences-section">
        <SectionHeading
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
                onChange={(e) => setCurrency(e.target.value)}
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
        </Card>
      </section>

      <section aria-labelledby="app-section">
        <SectionHeading
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
              <dd className="flex items-center gap-2 text-sm font-medium text-foreground">
                <CheckCircle2 className="h-4 w-4 text-success-500" aria-hidden="true" />
                Connected (gateway)
              </dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-muted">Authentication</dt>
              <dd className="text-sm font-medium text-foreground">
                {user?.email ?? "Signed in"}
              </dd>
            </div>
          </dl>
        </Card>
      </section>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave}>
          <Save className="h-4 w-4" aria-hidden="true" />
          Save changes
        </Button>
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-success-500">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            Saved locally
          </span>
        )}
      </div>
    </div>
  );
}
