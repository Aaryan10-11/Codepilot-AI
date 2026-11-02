import { httpRequest } from "./api";
import { agentSocket } from "./agent-ws";
import type { AgentRunEvent } from "../types/agents";
import type { SendMessageResponse } from "../types/chat";

export interface SendMessageInput {
  sessionId?: string | null;
  content: string;
  model?: string;
}

export interface SendMessageResult {
  sessionId: string;
  userMessageId: string;
  assistantMessageId: string;
}

class ChatService {
  async createSession(): Promise<string> {
    const response = await httpRequest<{ id: string }>("/sessions");
    return response.id;
  }

  async send(input: SendMessageInput): Promise<SendMessageResult> {
    const sessionId = input.sessionId ?? (await this.createSession());
    const response = await httpRequest<SendMessageResponse>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content: input.content, model: input.model }),
    });
    return { sessionId: response.session_id, userMessageId: response.user_message_id, assistantMessageId: response.assistant_message_id };
  }

  subscribe(sessionId: string, onEvent: (event: AgentRunEvent) => void, onStatus?: (status: "queued" | "running" | "completed" | "failed") => void) {
    agentSocket.connect(sessionId);
    const unsubscribe = agentSocket.onEvent((frame) => {
      if (frame.kind === "agent_event") onEvent(frame.event);
      else if (frame.kind === "run.status") onStatus?.(frame.status);
    });
    return unsubscribe;
  }
}

export const chatService = new ChatService();
