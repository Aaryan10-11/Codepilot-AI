import { Bot, Code2, FolderGit2, MessageSquare, Settings, SquarePen, X } from "lucide-react";
import { Link } from "react-router-dom";
import { useUIStore } from "../../stores/ui";
import { useAgentsStore } from "../../stores/agents";
import { cn } from "../../lib/utils";
import { StatusPill } from "../ui/status-pill";

const NAV_ITEMS = [
  { to: "/", label: "Chat", icon: MessageSquare, match: (p: string) => p === "/" },
  { to: "/agents", label: "Agent Studio", icon: Bot, match: (p: string) => p.startsWith("/agents") },
  { to: "/codebase", label: "Codebase", icon: FolderGit2, match: (p: string) => p.startsWith("/codebase") },
  { to: "/dsa", label: "Problems", icon: Code2, match: (p: string) => p.startsWith("/dsa") },
  { to: "/settings", label: "Settings", icon: Settings, match: (p: string) => p.startsWith("/settings") },
];

interface SidebarContentProps {
  collapsed: boolean;
  onNavigate?: () => void;
}

function SidebarContent({ collapsed, onNavigate }: SidebarContentProps) {
  const { contextPanelOpen, setContextPanelOpen, toggleSidebar } = useUIStore();
  const agents = useAgentsStore((state) => state.states);

  return (
    <div className={cn("relative flex h-full flex-col", collapsed ? "w-[56px] items-center px-2 py-3" : "w-[232px] px-3 py-3")}>
      <div className={cn("flex w-full items-center", collapsed ? "justify-center" : "gap-2")}>
        <div className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[8px] bg-accent text-bg">
          <Bot className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </div>
        {!collapsed ? <div className="truncate text-sm font-semibold tracking-tight">CodePilot</div> : null}
        {!collapsed ? (
          <button
            type="button"
            onClick={toggleSidebar}
            className="ml-auto rounded-full p-1.5 text-muted transition-colors hover:bg-raised hover:text-text"
            aria-label="Collapse sidebar"
          >
            <MessageSquare className="h-[14px] w-[14px]" strokeWidth={2} />
          </button>
        ) : null}
      </div>

      <nav className="mt-6 flex flex-col gap-1" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = item.match(window.location.pathname);
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 rounded-full px-3 py-2 text-sm transition-colors",
                collapsed ? "justify-center" : "w-full",
                active ? "bg-raised text-text" : "text-muted hover:bg-raised hover:text-text",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-[17px] w-[17px] shrink-0" strokeWidth={1.75} />
              {!collapsed ? <span className="truncate">{item.label}</span> : null}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-4 pt-6">
        <button
          type="button"
          className={cn(
            "flex items-center justify-center gap-2 rounded-full bg-text text-sm font-medium text-bg transition-opacity hover:opacity-90",
            collapsed ? "h-[34px] w-[34px]" : "h-[34px] w-full px-4",
          )}
        >
          <SquarePen className="h-[15px] w-[15px]" strokeWidth={2} />
          {!collapsed ? <span>New Session</span> : null}
        </button>

        <div className={cn("flex flex-col gap-3", collapsed && "items-center")}>
          <div className="flex items-center gap-2">
            <StatusPill status={agents.solver.status} />
            {!collapsed ? <span className="text-xs text-muted">Solver</span> : null}
          </div>
          <div className="flex items-center gap-2">
            <StatusPill status={agents.reviewer.status} />
            {!collapsed ? <span className="text-xs text-muted">Reviewer</span> : null}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setContextPanelOpen(!contextPanelOpen)}
          className={cn(
            "flex items-center gap-2 rounded-full p-2 text-muted transition-colors hover:bg-raised hover:text-text",
            collapsed ? "justify-center" : "w-full",
          )}
          aria-label="Toggle context panel"
        >
          <span className="flex h-[17px] w-[17px] items-center justify-center">
            <span className="h-[7px] w-[7px] rounded-full bg-accent" />
          </span>
          {!collapsed ? <span className="text-xs">Context</span> : null}
        </button>
      </div>
    </div>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, sidebarMobileOpen, setSidebarMobileOpen } = useUIStore();

  const asideClassName = [
    "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border bg-ground transition-transform duration-200 ease-out md:static md:z-auto md:transition-none",
    sidebarMobileOpen ? "translate-x-0" : "-translate-x-full",
    "top-0 h-[100svh] w-[232px]",
    sidebarCollapsed ? "md:w-[56px]" : "md:w-[232px]",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div>
      <aside className={asideClassName}>
        <SidebarContent collapsed={sidebarCollapsed} onNavigate={() => setSidebarMobileOpen(false)} />
        <button
          type="button"
          onClick={() => setSidebarMobileOpen(false)}
          className="absolute right-3 top-3 rounded-full p-2 text-muted hover:bg-raised hover:text-text md:hidden"
          aria-label="Close sidebar"
        >
          <X className="h-[16px] w-[16px]" strokeWidth={1.75} />
        </button>
      </aside>

      {sidebarMobileOpen ? (
        <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setSidebarMobileOpen(false)} aria-hidden="true" />
      ) : null}

      <button
        type="button"
        onClick={() => setSidebarMobileOpen(true)}
        className="fixed left-0 top-0 z-30 flex h-[40px] w-[40px] items-center justify-center border-r border-border bg-ground text-muted hover:text-text md:hidden"
        aria-label="Open sidebar"
      >
        <MessageSquare className="h-[18px] w-[18px]" strokeWidth={1.75} />
      </button>
    </div>
  );
}
