import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  theme: "dark" | "light";
  toggleTheme: () => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  sidebarMobileOpen: boolean;
  setSidebarMobileOpen: (open: boolean) => void;
  contextPanelOpen: boolean;
  setContextPanelOpen: (open: boolean) => void;
  contextPanelWidth: number;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: "dark",
      toggleTheme: () => set((state) => ({ theme: state.theme === "dark" ? "light" : "dark" })),
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      sidebarMobileOpen: false,
      setSidebarMobileOpen: (open) => set({ sidebarMobileOpen: open }),
      contextPanelOpen: true,
      setContextPanelOpen: (open) => set({ contextPanelOpen: open }),
      contextPanelWidth: 340,
    }),
    { name: "codepilot-ui" },
  ),
);
