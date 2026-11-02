import { useChatStore } from "../stores/chat";
import { useAgentsStore } from "../stores/agents";
import { StatusPill } from "../components/ui/status-pill";
import { MessageList } from "../components/chat/message-list";
import { Composer } from "../components/chat/composer";
import { WelcomeScreen } from "../components/chat/welcome-screen";

export function ChatWorkspacePage() {
  const messages = useChatStore((state) => state.messages);
  const sessionId = useChatStore((state) => state.sessionId);
  const agents = useAgentsStore((state) => state.states);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      {/* Header with provider health */}
      <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-6 pb-3 pt-3">
        <div>
          <h1 className="text-title font-semibold tracking-tight">Chat Workspace</h1>
          <p className="text-small text-muted">Context → Solve → Review → Execute</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill status={agents.context.status} />
          <StatusPill status={agents.solver.status} />
          <StatusPill status={agents.reviewer.status} />
        </div>
      </header>

      {/* Main content */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {isEmpty ? (
          <WelcomeScreen sessionId={sessionId} />
        ) : (
          <MessageList
            onApply={(messageId, code, path) => {
              useChatStore.getState().applySuggestion(messageId, {
                path: path ?? "generated-solution",
                language: "python",
                content: code,
                status: "pending",
              });
            }}
          />
        )}
      </div>

      {/* Composer section */}
      <div className="border-t border-border p-4">
        <Composer sessionId={sessionId} />
      </div>
    </div>
  );
}