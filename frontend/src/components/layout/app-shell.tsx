import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { ContextPanel } from "./context-panel";
import { useUIStore } from "../../stores/ui";

export function AppShell() {
  const { contextPanelOpen } = useUIStore();
  const location = useLocation();

  const isAgentSurface = location.pathname.startsWith("/workspace") || location.pathname === "/";

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <Outlet />
      </main>
      {isAgentSurface && contextPanelOpen ? <ContextPanel /> : null}
      {isAgentSurface && !contextPanelOpen ? (
        <button
          type="button"
          onClick={() => useUIStore.setState({ contextPanelOpen: true })}
          className="fixed right-0 top-0 z-40 hidden h-[40px] w-[40px] items-center justify-center border-l border-border bg-ground text-muted hover:text-text md:flex"
          aria-label="Open context panel"
        >
          <span className="h-[7px] w-[7px] rounded-full bg-accent" />
        </button>
      ) : null}
    </div>
  );
}
