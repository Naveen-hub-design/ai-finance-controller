import { forwardRef, type KeyboardEvent } from "react";
import { NavLink } from "react-router-dom";
import { Sparkles, X } from "lucide-react";
import {
  aiNavigation,
  footerNavigation,
  mainNavigation,
} from "../../lib/navigation";
import { cn } from "../../lib/cn";
import { useScrollLock } from "../../lib/useScrollLock";
import type { NavItem } from "../../types/navigation";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

function NavLinkItem({ item, onNavigate }: { item: NavItem; onNavigate: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors duration-150",
          "hover:bg-surface-raised hover:text-foreground",
          isActive && "bg-surface-raised text-foreground"
        )
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
      {item.label}
    </NavLink>
  );
}

function NavSection({
  items,
  onNavigate,
}: {
  items: NavItem[];
  onNavigate: () => void;
}) {
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <NavLinkItem key={item.to} item={item} onNavigate={onNavigate} />
      ))}
    </div>
  );
}

export const Sidebar = forwardRef<HTMLElement, SidebarProps>(
  ({ open, onClose }, ref) => {
    useScrollLock(open);

    const close = () => onClose();

    const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }

      if (event.key !== "Tab") return;

      const container = ref && typeof ref === "object" ? ref.current : null;
      if (!container) return;

      const focusable = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      ).filter(
        (el) =>
          el.offsetParent !== null ||
          el.getClientRects().length > 0 ||
          el === document.activeElement
      );

      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (active === first || active === container) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    return (
      <>
        {open && (
          <div
            aria-hidden="true"
            onClick={close}
            className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          />
        )}

        <aside
          id="app-sidebar"
          ref={ref}
          tabIndex={-1}
          role={open ? "dialog" : undefined}
          aria-modal={open ? true : undefined}
          aria-label="Navigation"
          onKeyDown={handleKeyDown}
          className={cn(
            "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-border bg-surface transition-transform duration-200 ease-out-quad lg:static lg:translate-x-0",
            open ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-600 text-white">
                <Sparkles className="h-4 w-4" aria-hidden="true" />
              </div>
              <div className="leading-tight">
                <div className="text-sm font-semibold text-foreground">
                  AI Finance Controller
                </div>
                <div className="text-[11px] text-muted-faint">Intelligent budgeting</div>
              </div>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Close navigation"
              className="rounded-lg p-1.5 text-muted transition-colors hover:bg-surface-raised hover:text-foreground lg:hidden"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
            <NavSection items={mainNavigation} onNavigate={close} />
            <div>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-faint">
                AI Insights
              </div>
              <NavSection items={aiNavigation} onNavigate={close} />
            </div>
            <NavSection items={footerNavigation} onNavigate={close} />
          </nav>

          <div className="border-t border-border px-5 py-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-raised text-muted">
                A
              </div>
              <div className="leading-tight">
                <div className="text-xs font-medium text-foreground">Demo User</div>
                <div className="text-[11px] text-muted-faint">Signed in · demo</div>
              </div>
            </div>
          </div>
        </aside>
      </>
    );
  }
);

Sidebar.displayName = "Sidebar";
