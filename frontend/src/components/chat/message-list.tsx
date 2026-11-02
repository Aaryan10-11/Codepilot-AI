import { useChatStore } from "../../stores/chat";
import { MarkdownContent } from "./markdown-content";

export interface MessageListProps {
  onApply: (messageId: string, code: string, path?: string) => void;
}

export function MessageList({ onApply }: MessageListProps) {
  const messages = useChatStore((state) => state.messages);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto pr-2 pb-2">
      {messages.map((message) => (
        <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex flex-col gap-2"}>
          {message.role === "user" ? (
            <div className="max-w-[80%] whitespace-pre-wrap rounded-[10px] border border-border bg-surface px-4 py-2.5 text-sm">
              {message.content}
            </div>
          ) : (
            <div className="min-w-0">
              <MarkdownContent content={message.content} streaming={message.status === "streaming"} onApply={(code, path) => onApply(message.id, code, path)} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
