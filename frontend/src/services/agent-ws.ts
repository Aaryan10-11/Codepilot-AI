import type { AgentSocketFrame } from "../types/agents";

const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined)?.replace(/^http/, "ws") ?? "ws://127.0.0.1:8000";

type FrameListener = (frame: AgentSocketFrame) => void;

/**
 * Minimal websocket subscriber for the agent event stream.
 *
 * Frames are normalized by the backend envelope:
 *   { kind: "agent_event", event: AgentRunEvent }
 *   { kind: "run.status", status: ... }
 *   { kind: "context.snapshot", context: ... }
 */
class AgentSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<FrameListener>();
  private sessionId: string | null = null;

  get connected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  get sessionIdValue(): string | null {
    return this.sessionId;
  }

  connect(sessionId: string): void {
    this.disconnect();
    this.sessionId = sessionId;
    const url = `${WS_URL}/v1/ws/sessions/${encodeURIComponent(sessionId)}`;
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {};
    socket.onmessage = (message) => {
      try {
        const frame = JSON.parse(String(message.data)) as AgentSocketFrame;
        for (const listener of this.listeners) listener(frame);
      } catch {
        // Malformed frames are dropped; the run keeps its last known state.
      }
    };
    socket.onclose = () => {
      this.socket = null;
      this.listeners.clear();
    };
    socket.onerror = () => {
      socket.close();
    };
  }

  disconnect(): void {
    this.sessionId = null;
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this.listeners.clear();
  }

  onEvent(listener: FrameListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }
}

export const agentSocket = new AgentSocketClient();
