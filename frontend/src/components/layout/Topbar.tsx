import { useEffect, useRef, useState, type Ref } from "react";
import {
  Menu,
  Search,
  Building2,
  User as UserIcon,
  Check,
  Sun,
  Moon,
} from "lucide-react";
import { useBusiness } from "../../context/BusinessContext";
import { useTheme } from "../../context/ThemeContext";
import { cn } from "../../lib/cn";

interface TopbarProps {
  onMenuClick: () => void;
  menuButtonRef?: Ref<HTMLButtonElement>;
  isMenuOpen?: boolean;
  menuControlsId?: string;
}

export function Topbar({
  onMenuClick,
  menuButtonRef,
  isMenuOpen = false,
  menuControlsId = "app-sidebar",
}: TopbarProps) {
  const { businesses, selectedBusinessId, selectedBusiness, selectBusiness } =
    useBusiness();
  const { theme, toggleTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const canSelectBusiness = businesses.length > 0;

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur-md sm:px-6">
      <button
        ref={menuButtonRef}
        type="button"
        onClick={onMenuClick}
        aria-label="Open navigation"
        aria-expanded={isMenuOpen}
        aria-controls={menuControlsId}
        className="rounded-lg p-2 text-muted transition-colors hover:bg-surface-raised hover:text-foreground lg:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </button>

      {canSelectBusiness && (
        <div ref={containerRef} className="relative">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-label="Switch business scope"
            className="flex h-10 items-center gap-2.5 rounded-xl border border-border bg-surface px-3.5 text-sm font-medium text-foreground shadow-sm transition-colors duration-150 hover:border-border-strong focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-500/10">
              {selectedBusiness ? (
                <Building2 className="h-3.5 w-3.5 text-accent-500" aria-hidden="true" />
              ) : (
                <UserIcon className="h-3.5 w-3.5 text-accent-500" aria-hidden="true" />
              )}
            </span>
            <span className="flex flex-col items-start leading-none">
              <span className="max-w-[10rem] truncate text-[13px] font-semibold">{selectedBusiness ? selectedBusiness.name : "Personal"}</span>
              <span className="text-[11px] font-normal text-muted-faint">{selectedBusiness ? (selectedBusiness.my_role === "OWNER" ? "Owner" : "Finance Manager") : "Personal scope"}</span>
            </span>
          </button>

          {open && (
            <div
              role="listbox"
              aria-label="Business scope"
              className="absolute right-0 top-full z-30 mt-2 w-64 overflow-hidden rounded-xl border border-border bg-surface shadow-lg"
            >
              <button
                type="button"
                role="option"
                aria-selected={selectedBusinessId === null}
                onClick={() => {
                  selectBusiness(null);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-surface-raised",
                  selectedBusinessId === null
                    ? "text-foreground"
                    : "text-muted"
                )}
              >
                <UserIcon className="h-4 w-4 shrink-0 text-accent-400" aria-hidden="true" />
                <span className="flex-1">Personal</span>
                {selectedBusinessId === null && (
                  <Check className="h-4 w-4 text-accent-400" aria-hidden="true" />
                )}
              </button>
              <div className="border-t border-border px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-faint">
                Businesses
              </div>
              {businesses.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  role="option"
                  aria-selected={selectedBusinessId === b.id}
                  onClick={() => {
                    selectBusiness(b.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-surface-raised",
                    selectedBusinessId === b.id
                      ? "text-foreground"
                      : "text-muted"
                  )}
                >
                  <Building2 className="h-4 w-4 shrink-0 text-accent-400" aria-hidden="true" />
                  <span className="flex-1 truncate">{b.name}</span>
                  {selectedBusinessId === b.id && (
                    <Check className="h-4 w-4 text-accent-400" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="relative hidden max-w-md flex-1 sm:block">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-faint"
          aria-hidden="true"
        />
        <input
          type="search"
          aria-label="Search"
          placeholder="Search accounts, transactions, insights..."
          className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 hover:border-border-strong focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none"
        />
      </div>

      <div className="ml-auto flex flex-1 justify-end lg:ml-0 lg:flex-none">
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={
            theme === "dark"
              ? "Switch to light mode"
              : "Switch to dark mode"
          }
          title={
            theme === "dark"
              ? "Switch to light mode"
              : "Switch to dark mode"
          }
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface text-muted transition-colors duration-150 hover:border-border-strong hover:text-foreground focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:outline-none"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Moon className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>
    </header>
  );
}
