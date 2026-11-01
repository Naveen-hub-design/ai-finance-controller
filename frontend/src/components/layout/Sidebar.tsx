import { forwardRef, type KeyboardEvent } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Sparkles, X, LogOut } from "lucide-react";
import {
  adminNavigation,
  aiNavigation,
  footerNavigation,
  mainNavigation,
} from "../../lib/navigation";
import { cn } from "../../lib/cn";
import { useScrollLock } from "../../lib/useScrollLock";
import { useAuth } from "../../context/AuthContext";
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
          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors duration-150",
          "hover:bg-surface-raised hover:text-foreground",
          isActive && "bg-surface-raised font-semibold text-foreground"
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            aria-hidden="true"
            className={cn(
              "absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent-500 transition-opacity",
              isActive ? "opacity-100" : "opacity-0"
            )}
          />
          <Icon
            className={cn(
              "h-[18px] w-[18px] shrink-0 transition-colors",
              isActive ? "text-accent-400" : "text-muted group-hover:text-foreground"
            )}
            aria-hidden="true"
          />
          {item.label}
        </>
      )}
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

function visibleFor(
  items: NavItem[],
  role: string | undefined
): NavItem[] {
  return items.filter((item) => {
    if (!item.allowedRoles) return true;
    return role !== undefined && item.allowedRoles.includes(role as never);
  });
}

export const Sidebar = forwardRef<HTMLElement, SidebarProps>(
  ({ open, onClose }, ref) => {
    useScrollLock(open);

    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const role = user?.role;

    const close = () => onClose();

    const handleSignOut = () => {
      logout();
      navigate("/login", { replace: true });
    };

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
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 text-white shadow-sm">
                <Sparkles className="h-4 w-4" aria-hidden="true" />
              </div>
              <div className="leading-tight">
                <div className="text-sm font-semibold tracking-tight text-foreground">
                  AI Finance Controller
                </div>
                <div className="text-[11px] text-muted-faint font-medium">Enterprise Financial Controls</div>
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
            {visibleFor(adminNavigation, role).length > 0 && (
              <div>
                <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-faint">System</div>
                <NavSection items={visibleFor(adminNavigation, role)} onNavigate={close} />
              </div>
            )}
            {visibleFor(mainNavigation, role).some((i) => ["Dashboard","Accounts","Transactions","Categories","Budgets","Goals"].includes(i.label)) && (
              <div>
                <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-faint">Workspace</div>
                <NavSection items={visibleFor(mainNavigation, role).filter((i) => ["Dashboard","Accounts","Transactions","Categories","Budgets","Goals"].includes(i.label))} onNavigate={close} />
              </div>
            )}
            {visibleFor(mainNavigation, role).some((i) => i.label === "Businesses") && (
              <div>
                <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-faint">Business</div>
                <NavSection items={visibleFor(mainNavigation, role).filter((i) => i.label === "Businesses")} onNavigate={close} />
              </div>
            )}
            <div>
              <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-faint">Intelligence</div>
              <NavSection items={visibleFor(aiNavigation, role)} onNavigate={close} />
            </div>
            <div>
              <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-faint">System</div>
              <NavSection items={visibleFor(footerNavigation, role)} onNavigate={close} />
            </div>
          </nav>

          <div className="border-t border-border px-5 py-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-raised text-xs font-semibold uppercase text-muted">
                {(user?.full_name?.charAt(0) ?? user?.email?.charAt(0) ?? "A")}
              </div>
              <div className="min-w-0 leading-tight">
                <div className="truncate text-xs font-medium text-foreground">
                  {user?.full_name || user?.email || "Signed in"}
                </div>
                <div className="truncate text-[11px] text-muted-faint">
                  {user?.email ?? "Account"}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="mt-3 inline-flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors duration-150 hover:bg-surface-raised hover:text-foreground"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </aside>
      </>
    );
  }
);

Sidebar.displayName = "Sidebar";
