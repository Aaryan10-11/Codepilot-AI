import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { RightPanel } from "./right-panel";
import { useUIStore } from "../../stores/ui";

export function AppShell() {
  const { contextPanelOpen } = useUIStore();
  const location = useLocation();

  const isAgentSurface = location.pathname === "/" || location.pathname.startsWith("/workspace");

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col bg-bg">
        <Topbar title={location.pathname === "/" ? "Chat Workspace" : location.pathname.replace("/", "").toUpperCase()} />
        <main className="app-main flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      {isAgentSurface && contextPanelOpen ? <RightPanel /> : null}
    </div>
  );
}
