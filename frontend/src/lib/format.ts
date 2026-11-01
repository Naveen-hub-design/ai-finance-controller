const DEFAULT_CURRENCY = "INR";
const CURRENCY_KEY = "ai_finance_display_currency";

export function getDisplayCurrency(): string {
  try {
    return window.localStorage.getItem(CURRENCY_KEY) || DEFAULT_CURRENCY;
  } catch {
    return DEFAULT_CURRENCY;
  }
}

export function setDisplayCurrency(code: string): void {
  try {
    window.localStorage.setItem(CURRENCY_KEY, code);
  } catch {
    // Storage unavailable; format falls back to the default currency.
  }
}

function toNumber(
  value: string | number | null | undefined
): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function parseDateOnly(value: string): { y: number; m: number; d: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  return { y: Number(match[1]), m: Number(match[2]), d: Number(match[3]) };
}

export function formatCurrency(
  value: string | number | null | undefined,
  currency?: string
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const code = currency || getDisplayCurrency();
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `${n.toFixed(2)} ${code}`;
  }
}

export function formatCompactCurrency(
  value: string | number | null | undefined,
  currency?: string
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const code = currency || getDisplayCurrency();
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: code,
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(n);
  } catch {
    return `${n.toFixed(0)} ${code}`;
  }
}

export function formatNumber(
  value: string | number | null | undefined,
  maximumFractionDigits = 2
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits,
  }).format(n);
}

export function formatPercent(
  value: string | number | null | undefined,
  maximumFractionDigits = 1
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `${n.toFixed(maximumFractionDigits)}%`;
}

export function formatDate(
  value: string | Date | null | undefined
): string {
  if (!value) return "—";
  if (typeof value === "string") {
    const parts = parseDateOnly(value);
    if (parts) {
      return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(new Date(parts.y, parts.m - 1, parts.d));
    }
  }
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
}

export function formatDateTime(
  value: string | Date | null | undefined
): string {
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(d);
}

export function formatShortDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  if (typeof value === "string") {
    const parts = parseDateOnly(value);
    if (parts) {
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
      }).format(new Date(parts.y, parts.m - 1, parts.d));
    }
  }
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(d);
}

export function formatMonthYear(value: string | Date | null | undefined): string {
  if (!value) return "—";
  if (typeof value === "string") {
    const parts = parseDateOnly(value);
    if (parts) {
      return new Intl.DateTimeFormat("en-US", {
        month: "long",
        year: "numeric",
      }).format(new Date(parts.y, parts.m - 1, parts.d));
    }
  }
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(d);
}
