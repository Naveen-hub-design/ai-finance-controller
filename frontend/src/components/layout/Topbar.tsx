import { Menu, Search } from "lucide-react";

interface TopbarProps {
  onMenuClick: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur-md sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Open navigation"
        className="rounded-lg p-2 text-muted transition-colors hover:bg-surface-raised hover:text-foreground lg:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </button>

      <div className="relative hidden max-w-md flex-1 sm:block">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-faint"
          aria-hidden="true"
        />
        <input
          type="search"
          placeholder="Search accounts, transactions, insights..."
          className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-foreground placeholder:text-muted-faint transition-colors duration-150 focus:border-accent-500 focus:outline-none"
        />
      </div>
    </header>
  );
}
