import type { ContextFileRef, TokenUsage } from "./agents";

export type MessageStatus = "streaming" | "completed" | "error";

export interface ChatMessage {
  id: string;
  session_id?: string;
  role: "user" | "assistant";
  content: string;
  created_at: number;
  status: MessageStatus;
  model?: string;
  token_usage?: TokenUsage;
  files?: ContextFileRef[];
}

export interface SendMessageResponse {
  session_id: string;
  user_message_id: string;
  assistant_message_id: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
}
