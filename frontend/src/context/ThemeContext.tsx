import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Theme = "light" | "dark";

const THEME_KEY = "ai_finance_theme";
const ROOT_ATTR = "data-theme";

export interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredTheme(): Theme | null {
  try {
    const raw = window.localStorage.getItem(THEME_KEY);
    if (raw === "light" || raw === "dark") return raw;
    return null;
  } catch {
    return null;
  }
}

function systemTheme(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: light)")?.matches
    ? "light"
    : "dark";
}

function applyRootTheme(theme: Theme): void {
  document.documentElement.setAttribute(ROOT_ATTR, theme);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = readStoredTheme();
    return stored ?? systemTheme();
  });

  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    applyRootTheme(theme);
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setTransitioning(true);
    setThemeState(next);
    window.setTimeout(() => setTransitioning(false), 220);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const next = current === "light" ? "dark" : "light";
      setTransitioning(true);
      window.setTimeout(() => setTransitioning(false), 220);
      return next;
    });
  }, []);

  // Respect reduced motion on the root.
  useEffect(() => {
    const htmlEl = document.documentElement;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")
      ?.matches;
    if (transitioning && !reduce) {
      htmlEl.classList.add("theme-transition");
    } else {
      htmlEl.classList.remove("theme-transition");
    }
  }, [transitioning]);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}
