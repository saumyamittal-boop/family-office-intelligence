import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import type { SessionInfo } from "../api/client";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { SidePanel } from "../ui/Overlays";
import { Brand, NavList, Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useSidebarCollapsed } from "./useSidebar";

/**
 * The frame around every signed-in page: skip link, collapsible sidebar (a drawer on small screens),
 * top bar and the main landmark.
 */
export function AppShell({ session }: { session: SessionInfo }) {
  const [collapsed, toggle] = useSidebarCollapsed();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  return (
    <div className={`shell ${collapsed ? "is-collapsed" : ""}`}>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className="shell-main">
        <Topbar session={session} onOpenNav={() => setDrawerOpen(true)} />
        <main id="main" tabIndex={-1} className="content">
          <ErrorBoundary resetKey={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <SidePanel open={drawerOpen} onOpenChange={setDrawerOpen} title="Navigation" side="left">
        <Brand />
        <NavList onNavigate={() => setDrawerOpen(false)} />
      </SidePanel>
    </div>
  );
}
