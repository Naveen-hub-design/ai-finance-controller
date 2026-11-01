import { useEffect, useRef, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/layout/Sidebar";
import { Topbar } from "../components/layout/Topbar";

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sidebarRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (sidebarOpen) {
      sidebarRef.current?.focus();
    } else if (wasOpen.current) {
      menuButtonRef.current?.focus();
    }
    wasOpen.current = sidebarOpen;
  }, [sidebarOpen]);

  return (
    <div className="flex min-h-screen bg-background">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>

      <Sidebar
        ref={sidebarRef}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          menuButtonRef={menuButtonRef}
          isMenuOpen={sidebarOpen}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main
          id="main"
          tabIndex={-1}
          className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8"
        >
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
