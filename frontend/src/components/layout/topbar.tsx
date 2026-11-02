import { Search, Bell, Settings, Command } from "lucide-react";
import { useUIStore } from "../../stores/ui";
import { useState } from "react";

export function Topbar({ title = "Workspace", subtitle }: { title?: string; subtitle?: string }) {
  const { toggleTheme } = useUIStore();
  const [commandOpen, setCommandOpen] = useState(false);

  return (
    <>
      <header className="flex h-[48px] items-center justify-between border-b border-border bg-surface px-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setCommandOpen(true)}
            className="flex items-center gap-2 rounded-[8px] border border-border bg-ground px-3 py-1.5 text-xs text-muted hover:bg-raised hover:text-text"
          >
            <Search className="h-3.5 w-3.5" />
            Search
            <kbd className="ml-auto rounded-[4px] bg-raised px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
          </button>
          <div className="h-4 w-px bg-border" />
          <h2 className="text-sm font-semibold">{title}</h2>
          {subtitle && <span className="text-xs text-muted">· {subtitle}</span>}
        </div>

        <div className="flex items-center gap-2">
          <button aria-label="Notifications" className="rounded-[8px] p-2 text-muted hover:bg-raised hover:text-text">
            <Bell className="h-4 w-4" />
          </button>
          <button aria-label="Settings" className="rounded-[8px] p-2 text-muted hover:bg-raised hover:text-text" onClick={toggleTheme}>
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </header>

      {commandOpen && (
        <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} />
      )}
    </>
  );
}

function CommandPalette({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute left-1/2 top-[20%] w-[min(640px,90vw)] -translate-x-1/2 rounded-[12px] border border-border bg-surface p-4 shadow-xl">
        <div className="flex items-center gap-2 rounded-[8px] border border-border bg-ground px-3 py-2 text-sm text-muted">
          <Search className="h-4 w-4" />
          <input autoFocus placeholder="Search sessions, files, commands..." className="w-full bg-transparent outline-none text-text placeholder:text-muted" />
          <kbd className="rounded-[4px] bg-raised px-1.5 py-0.5 font-mono text-[10px]">ESC</kbd>
        </div>
        <ul className="mt-3 space-y-1 text-xs">
          {["New Chat Session", "Agent Studio", "Codebase Explorer", "DSA Practice", "Project Settings"].map((item) => (
            <li key={item} className="rounded-[6px] px-3 py-2 hover:bg-raised hover:text-text cursor-pointer flex items-center justify-between">
              <span>{item}</span>
              <Command className="h-3.5 w-3.5 text-muted" />
            </li>
          ))}
        </ul>
        <button onClick={onClose} className="mt-4 w-full rounded-[8px] border border-border py-2 text-xs text-muted hover:bg-raised hover:text-text">
          Close Command Palette
        </button>
      </div>
    </div>
  );
}
