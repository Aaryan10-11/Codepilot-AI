import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ArrowUp, Square } from "lucide-react";
import { useChatStore } from "../../stores/chat";
import { useSettingsStore } from "../../stores/settings";
import { Button } from "../ui/button";
import { Textarea } from "../ui/inputs";

export interface ComposerProps {
  sessionId?: string | null;
  placeholder?: string;
}

export function Composer({ sessionId, placeholder }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { send, isStreaming, stop } = useChatStore();
  const { models } = useSettingsStore();

  const autoresize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  };

  useEffect(() => {
    autoresize();
  }, [value]);

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  };

  const submit = () => {
    const text = value.trim();
    if (!text || isStreaming) return;
    void send({ sessionId: sessionId ?? undefined, content: text, model: models.solver });
    setValue("");
  };

  const canSend = value.trim().length > 0 && !isStreaming;

  return (
    <div className="w-full">
      <div className="rounded-[10px] border border-border bg-surface p-3 focus-within:border-accent">
        <Textarea
          ref={textareaRef as never}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            autoresize();
          }}
          onKeyDown={onKeyDown}
          placeholder={placeholder ?? "Describe the bug, the algorithm, or the feature…"}
          aria-label="Message CodePilot"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-xs text-muted">Enter to send · Shift+Enter for a new line</span>
          {isStreaming ? (
            <Button variant="secondary" size="sm" onClick={stop} aria-label="Stop generating">
              <Square className="h-3 w-3" fill="currentColor" />
              Stop
            </Button>
          ) : (
            <Button size="sm" onClick={submit} disabled={!canSend}>
              <ArrowUp className="h-3.5 w-3.5" strokeWidth={2} />
              Send
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
