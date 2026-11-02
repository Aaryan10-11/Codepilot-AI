import { useEffect } from "react";

export function NotFoundPage() {
  useEffect(() => {
    document.title = "Page not found · CodePilot AI";
  }, []);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="max-w-md text-sm text-muted">The page you requested does not exist.</p>
      <a className="text-sm text-accent underline-offset-4 hover:underline" href="/">
        Back to chat
      </a>
    </div>
  );
}
