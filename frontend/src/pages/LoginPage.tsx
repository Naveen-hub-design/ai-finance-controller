import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  ArrowRight,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  ShieldCheck,
  Store,
  UserCog,
  BrainCircuit,
  ShieldAlert,
  ThumbsUp,
  Landmark,
  Activity,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../lib/types";
import { cn } from "../lib/cn";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const FEATURES = [
  {
    icon: BrainCircuit,
    title: "AI Financial Intelligence",
    description: "Source-grounded answers about your finances.",
  },
  {
    icon: ShieldAlert,
    title: "Anomaly & Risk Detection",
    description: "Early signals across accounts and categories.",
  },
  {
    icon: ThumbsUp,
    title: "Financial Recommendations",
    description: "Concrete, actionable suggestions for cash flow.",
  },
  {
    icon: Landmark,
    title: "AI Finance Controller",
    description: "Proposal-only controller decisions, never money movement.",
  },
  {
    icon: Activity,
    title: "Business Financial Management",
    description: "Personal and business scope in one platform.",
  },
] as const;

const DEMO_ROLES: {
  key: Role;
  title: string;
  description: string;
  icon: typeof Store;
  accent: string;
  bg: string;
}[] = [
  {
    key: "PLATFORM_ADMIN",
    title: "Platform Admin",
    description: "Manage platform users and businesses",
    icon: ShieldCheck,
    accent: "text-accent-400",
    bg: "bg-accent-600/10",
  },
  {
    key: "MERCHANT",
    title: "Merchant",
    description: "Business finance & AI insights",
    icon: Store,
    accent: "text-success-500",
    bg: "bg-success-600/10",
  },
  {
    key: "FINANCE_MANAGER",
    title: "Finance Manager",
    description: "Financial operations & analysis",
    icon: UserCog,
    accent: "text-warning-500",
    bg: "bg-warning-600/10",
  },
];

function postLoginPath(role: Role | undefined): string {
  if (role === "PLATFORM_ADMIN") return "/admin";
  return "/dashboard";
}

export default function LoginPage() {
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState<{
    email?: boolean;
    password?: boolean;
  }>({});
  const [submitting, setSubmitting] = useState(false);
  const [demoRole, setDemoRole] = useState<Role | null>(null);
  const [error, setError] = useState<string | null>(null);

  const emailError = useMemo(() => {
    const value = email.trim();
    if (!value) return "Email is required.";
    if (!EMAIL_PATTERN.test(value)) return "Enter a valid email address.";
    return null;
  }, [email]);

  const passwordError = useMemo(() => {
    if (!password) return "Password is required.";
    return null;
  }, [password]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setTouched({ email: true, password: true });

    if (submitting || demoRole) return;
    if (emailError || passwordError) return;

    setError(null);
    setSubmitting(true);

    try {
      const role = await login(email.trim(), password);
      navigate(postLoginPath(role), { replace: true });
    } catch (err) {
      const message =
        (err as { message?: string })?.message || "Unable to sign in.";
      if (/invalid email or password/i.test(message)) {
        setError("Invalid email or password.");
      } else if (/failed|network|connect|fetch/i.test(message)) {
        setError("Unable to connect. Check your connection and try again.");
      } else {
        setError(message);
      }
      setSubmitting(false);
    }
  };

  const handleDemoLogin = async (role: Role) => {
    if (submitting || demoRole) return;
    setError(null);
    setDemoRole(role);
    try {
      const authenticatedRole = await demoLogin(role);
      navigate(postLoginPath(authenticatedRole), { replace: true });
    } catch (err) {
      const message =
        (err as { message?: string })?.message || "Unable to sign in.";
      if (/forbidden/i.test(message)) {
        setError("Demo login is not available in this environment.");
      } else if (/failed|network|connect|fetch/i.test(message)) {
        setError("Unable to connect. Check your connection and try again.");
      } else {
        setError(message);
      }
      setDemoRole(null);
    }
  };

  const showEmailError = touched.email && emailError !== null;
  const showPasswordError = touched.password && passwordError !== null;
  const busy = submitting || demoRole !== null;

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      {/* Atmospheric background */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
      >
        <div className="absolute -left-40 -top-40 h-[600px] w-[600px] rounded-full bg-accent-600/8 blur-[140px]" />
        <div className="absolute -right-32 bottom-[-120px] h-[500px] w-[500px] rounded-full bg-accent-800/8 blur-[130px]" />
        <div className="absolute left-1/2 top-1/3 h-[350px] w-[350px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent-700/5 blur-[100px]" />
      </div>

      {/* Main layout */}
      <div className="relative z-10 flex min-h-screen">
        {/* ── Left panel: branding + atmosphere ── */}
        <div className="pointer-events-none hidden w-1/2 lg:flex lg:flex-col lg:justify-center lg:px-16 xl:px-20">
          {/* Animated grid */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.025]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(47,111,230,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(47,111,230,0.6) 1px, transparent 1px)",
              backgroundSize: "56px 56px",
            }}
          />

          {/* Floating shapes */}
          <div className="animate-float absolute left-[14%] top-[18%] h-3 w-3 rounded-full bg-accent-500/20" />
          <div className="animate-float-reverse absolute left-[58%] top-[12%] h-2.5 w-2.5 rotate-45 rounded-sm bg-accent-400/15" />
          <div className="animate-float absolute right-[18%] top-[32%] h-4 w-4 rounded-full bg-accent-600/10" />
          <div className="animate-float-reverse absolute left-[38%] bottom-[22%] h-3 w-3 rounded-full bg-accent-500/12" />
          <div className="animate-float absolute left-[72%] top-[52%] h-2 w-2 rotate-12 bg-accent-400/18" />
          <div className="animate-glow-pulse absolute left-[25%] top-[45%] h-20 w-20 rounded-full bg-accent-600/8 blur-2xl" />
          <div className="animate-glow-pulse absolute right-[12%] bottom-[35%] h-16 w-16 rounded-full bg-accent-500/6 blur-2xl animation-delay-150" />

          {/* Content */}
          <div className="animate-rise relative pointer-events-auto">
            {/* Logo */}
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-500 to-accent-700 text-white shadow-[0_14px_44px_-10px_rgba(47,111,230,0.55)]">
                <Sparkles className="h-7 w-7" aria-hidden="true" />
              </div>
              <div>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  AI Finance Controller
                </div>
                <div className="text-sm text-muted">
                  Intelligent financial control for modern businesses
                </div>
              </div>
            </div>

            {/* Headline */}
            <h1 className="mt-12 max-w-lg text-[2.75rem] font-bold leading-[1.1] tracking-tight text-foreground">
              Understand, protect, and control your finances with precision.
            </h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted">
              A role-aware, business-aware financial intelligence platform that
              combines real account data with grounded AI insights, risk
              detection, and proposal-only guidance.
            </p>

            {/* Feature grid */}
            <div className="mt-12 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {FEATURES.map((f) => {
                const Icon = f.icon;
                return (
                  <div
                    key={f.title}
                    className="flex items-start gap-3 rounded-xl border border-border/50 bg-surface/40 p-4 backdrop-blur-sm transition-colors duration-150 hover:border-border-strong hover:bg-surface/60"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-600/10 text-accent-400">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-foreground">
                        {f.title}
                      </div>
                      <div className="mt-1 text-xs leading-relaxed text-muted">
                        {f.description}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Right panel: login + demo ── */}
        <div className="flex w-full items-center justify-center px-6 py-10 lg:w-1/2 lg:px-12 xl:px-16">
          <div className="w-full max-w-md">
            {/* Mobile logo */}
            <div className="mb-8 text-center lg:hidden">
              <div className="mb-3 inline-flex items-center gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 text-white shadow-lg">
                  <Sparkles className="h-5 w-5" aria-hidden="true" />
                </div>
                <span className="text-lg font-bold tracking-tight text-foreground">
                  AI Finance Controller
                </span>
              </div>
              <p className="text-sm text-muted">
                Intelligent financial control for modern businesses.
              </p>
            </div>

            <div className="animate-rise space-y-5">
              {/* Login card */}
              <Card className="border-border/60 p-7 shadow-card sm:p-8">
                <div className="mb-7">
                  <h2 className="text-xl font-bold tracking-tight text-foreground">
                    Welcome back
                  </h2>
                  <p className="mt-1.5 text-sm text-muted">
                    Sign in to your account to continue.
                  </p>
                </div>

                <form
                  className="space-y-5"
                  onSubmit={handleSubmit}
                  noValidate
                >
                  {/* Email */}
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
                      required
                      autoComplete="email"
                      inputMode="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (error) setError(null);
                      }}
                      onBlur={() =>
                        setTouched((t) => ({ ...t, email: true }))
                      }
                      disabled={busy}
                      aria-invalid={showEmailError || undefined}
                      aria-describedby={
                        showEmailError ? "email-error" : undefined
                      }
                      className={cn(
                        showEmailError && "border-danger-500/70"
                      )}
                    />
                    {showEmailError && (
                      <p
                        id="email-error"
                        className="mt-1.5 text-xs text-danger-400"
                      >
                        {emailError}
                      </p>
                    )}
                  </div>

                  {/* Password */}
                  <div>
                    <label
                      htmlFor="password"
                      className="mb-1.5 block text-sm font-medium text-muted"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        required
                        autoComplete="current-password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          if (error) setError(null);
                        }}
                        onBlur={() =>
                          setTouched((t) => ({ ...t, password: true }))
                        }
                        disabled={busy}
                        aria-invalid={showPasswordError || undefined}
                        aria-describedby={
                          showPasswordError ? "password-error" : undefined
                        }
                        className={cn(
                          "pr-11",
                          showPasswordError && "border-danger-500/70"
                        )}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((s) => !s)}
                        disabled={busy}
                        aria-label={
                          showPassword ? "Hide password" : "Show password"
                        }
                        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-muted transition-colors duration-150 hover:text-foreground focus:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" aria-hidden="true" />
                        ) : (
                          <Eye className="h-4 w-4" aria-hidden="true" />
                        )}
                      </button>
                    </div>
                    {showPasswordError && (
                      <p
                        id="password-error"
                        className="mt-1.5 text-xs text-danger-400"
                      >
                        {passwordError}
                      </p>
                    )}
                  </div>

                  {/* Error */}
                  <div aria-live="polite">
                    {error && (
                      <div
                        role="alert"
                        className="flex items-start gap-2.5 rounded-lg border border-danger-500/25 bg-danger-500/5 px-3.5 py-3 text-sm text-danger-400"
                      >
                        <AlertCircle
                          className="mt-0.5 h-4 w-4 shrink-0"
                          aria-hidden="true"
                        />
                        <span>{error}</span>
                      </div>
                    )}
                  </div>

                  {/* Submit */}
                  <Button
                    type="submit"
                    size="lg"
                    className="w-full"
                    disabled={busy}
                    aria-busy={submitting}
                  >
                    {submitting ? (
                      <>
                        <Loader2
                          className="h-4 w-4 animate-spin"
                          aria-hidden="true"
                        />
                        Signing in…
                      </>
                    ) : (
                      <>
                        Continue
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </>
                    )}
                  </Button>
                </form>
              </Card>

              {/* Demo login section */}
              <div>
                <div className="mb-4 flex items-center gap-3">
                  <span className="h-px flex-1 bg-border" aria-hidden="true" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-faint">
                    Quick demo access
                  </span>
                  <span className="h-px flex-1 bg-border" aria-hidden="true" />
                </div>

                <div className="space-y-2.5">
                  {DEMO_ROLES.map((role) => {
                    const Icon = role.icon;
                    const loading = demoRole === role.key;
                    return (
                      <button
                        key={role.key}
                        type="button"
                        disabled={busy}
                        onClick={() => handleDemoLogin(role.key)}
                        aria-busy={loading}
                        className={cn(
                          "card-interactive group flex w-full items-center gap-3.5 rounded-xl border border-border bg-surface px-4 py-3.5 text-left transition-colors duration-150 hover:border-border-strong hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-60"
                        )}
                      >
                        <div
                          className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                            role.bg,
                            role.accent
                          )}
                        >
                          {loading ? (
                            <Loader2
                              className="h-4 w-4 animate-spin"
                              aria-hidden="true"
                            />
                          ) : (
                            <Icon className="h-4 w-4" aria-hidden="true" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-foreground">
                            {role.title}
                          </div>
                          <div className="mt-0.5 text-xs text-muted truncate">
                            {role.description}
                          </div>
                        </div>
                        <ArrowRight
                          className="h-4 w-4 shrink-0 text-muted-faint transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-foreground"
                          aria-hidden="true"
                        />
                      </button>
                    );
                  })}
                </div>

                <p className="mt-3 text-center text-xs text-muted-faint">
                  One-click demo access — development only, same authenticated
                  flow as normal login.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
