import { useEffect, useRef, useState } from "react";
import { Square } from "lucide-react";
import { useChatStore } from "../../stores/chat";
import { useSettingsStore } from "../../stores/settings";
import { Button } from "../ui/button";
import { Textarea } from "../ui/inputs";
import { Select } from "../ui/inputs";

export interface ComposerProps {
  sessionId?: string | null;
  placeholder?: string;
}

export function Composer({ sessionId, placeholder }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { send, isStreaming, stop } = useChatStore();
  const { models, setModel, setProviderId, providerOptions } = useSettingsStore();

  const autoresize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  };

  useEffect(() => {
    autoresize();
  }, [value]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
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

  // Build model options with unique keys
  const modelOptions = [
    { label: "Solver model", value: models.solver },
  ];

  return (
    <div className="w-full">
      <div className="rounded-[10px] border border-border bg-surface p-3 focus-within:border-accent">
        <Textarea
          ref={textareaRef}
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
            <div className="flex items-center gap-2">
              <Select
                value={models.solver}
                onChange={(event: React.ChangeEvent<HTMLSelectElement>) => setModel("solver", event.target.value)}
                aria-label="Model"
              >
                {modelOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
              {providerOptions.map((opt) => (
                <Button
                  key={opt.id}
                  variant="secondary"
                  size="sm"
                  onClick={() => setProviderId(opt.id)}
                  className="text-xs"
                >
                  {opt.name}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}