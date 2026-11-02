import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/app-shell";
import { ChatWorkspacePage } from "./pages/workspace";
import { DSAPage } from "./pages/dsa";
import { SettingsPage } from "./pages/settings";
import { NotFoundPage } from "./pages/not-found";
import { useUIStore } from "./stores/ui";

function ThemeSync() {
  const theme = useUIStore((state) => state.theme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  return null;
}

export default function App() {
  return (
    <>
      <ThemeSync />
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<ChatWorkspacePage />} />
          <Route path="workspace/:sessionId" element={<ChatWorkspacePage />} />
          <Route path="dsa" element={<DSAPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </>
  );
}
