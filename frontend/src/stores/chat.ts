import { create } from "zustand";
import { chatService, type SendMessageInput } from "../services/chat";
import type { ContextFileRef, TokenUsage } from "../types/agents";
import type { ChatMessage, MessageStatus } from "../types/chat";

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  send: (input: SendMessageInput) => Promise<void>;
  stop: () => void;
  clear: () => void;
  setSessionId: (id: string) => void;
  appendDelta: (messageId: string, text: string) => void;
  setMessageStatus: (id: string, status: MessageStatus) => void;
  setMessageFiles: (id: string, files: ContextFileRef[]) => void;
  setMessageTokens: (id: string, tokens: TokenUsage | undefined) => void;
  applySuggestion: (messageId: string, file: ContextFileRef) => void;
}

let localCounter = 0;
let activeUnsubscribe: (() => void) | undefined;

function createLocalId(prefix: string): string {
  localCounter += 1;
  return `${prefix}_${Date.now()}_${localCounter}`;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessionId: null,
  messages: [],
  isStreaming: false,
  streamingMessageId: null,

  send: async (input) => {
    const content = input.content.trim();
    if (!content || get().isStreaming) return;

    const userMessage = createLocalMessage("user", content);
    const assistantMessage = createLocalMessage("assistant", "");
    assistantMessage.status = "streaming";

    set((state) => ({
      sessionId: input.sessionId ?? state.sessionId,
      isStreaming: true,
      streamingMessageId: assistantMessage.id,
      messages: [...state.messages, userMessage, assistantMessage],
    }));

    let sessionId = get().sessionId;
    try {
      const run = await chatService.send({ ...input, sessionId });
      sessionId = run.sessionId;
      set({ sessionId });

      let unsubscribe: (() => void) | undefined;
      unsubscribe = chatService.subscribe(
        sessionId,
        (event) => {
          if (event.type === "solver.delta") {
            get().appendDelta(assistantMessage.id, event.text);
          }
          if (event.type === "solver.status") {
            if (event.status === "failed") get().setMessageStatus(assistantMessage.id, "error");
          }
          if (event.type === "solver.code") {
            get().setMessageFiles(assistantMessage.id, [
              {
                path: event.path,
                language: event.language,
                content: event.content,
                score: undefined,
                preview: undefined,
              },
            ]);
          }
          if (event.type === "context.tokens") {
            get().setMessageTokens(assistantMessage.id, event.tokens);
          }
        },
        (status) => {
          if (status === "completed") {
            set({ isStreaming: false, streamingMessageId: null });
          }
          if (status === "failed") {
            get().setMessageStatus(assistantMessage.id, "error");
          }
        },
      );
      activeUnsubscribe = unsubscribe;
    } catch (error) {
      get().setMessageStatus(assistantMessage.id, "error");
      throw error;
    }
  },

  stop: () => {
    set({ isStreaming: false, streamingMessageId: null });
    activeUnsubscribe?.();
    activeUnsubscribe = undefined;
  },
  clear: () => set({ messages: [], streamingMessageId: null, isStreaming: false }),
  setSessionId: (id) => set({ sessionId: id }),
  appendDelta: (messageId, text) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === messageId ? { ...m, content: m.content + text, status: "streaming" } : m)),
    })),
  setMessageStatus: (id, status) =>
    set((state) => ({ messages: state.messages.map((m) => (m.id === id ? { ...m, status } : m)) })),
  setMessageFiles: (id, files) =>
    set((state) => ({ messages: state.messages.map((m) => (m.id === id ? { ...m, files } : m)) })),
  setMessageTokens: (id, tokens) =>
    set((state) => ({ messages: state.messages.map((m) => (m.id === id ? { ...m, token_usage: tokens } : m)) })),
  applySuggestion: (messageId, file) =>
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.id !== messageId) return m;
        const files = m.files?.map((f) => (f.path === file.path ? { ...f, status: "applied" as const } : f)) ?? [file];
        return { ...m, files };
      }),
    })),
}));

function createLocalMessage(role: "user" | "assistant", content: string): ChatMessage {
  return {
    id: createLocalId(role === "user" ? "u" : "a"),
    role,
    content,
    created_at: Date.now(),
    status: "completed",
  };
}
