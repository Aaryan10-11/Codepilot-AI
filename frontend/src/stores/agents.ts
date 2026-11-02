import { create } from "zustand";
import { AGENT_IDS, type AgentId, type AgentState, type ContextFileRef, type ExecutionResult, type TokenUsage } from "../types/agents";

export const idleAgentState = (agent: AgentId): AgentState => ({
  agent,
  status: "idle",
  updated_at: Date.now(),
});

interface AgentsState {
  states: Record<AgentId, AgentState>;
  files: ContextFileRef[];
  tokens: TokenUsage | null;
  execution: ExecutionResult | null;
  setAgentState: (agent: AgentId, patch: Partial<AgentState>) => void;
  setAgentsStatus: (statuses: Partial<Record<AgentId, AgentState["status"]>>) => void;
  setFiles: (files: ContextFileRef[]) => void;
  setTokens: (tokens: TokenUsage | null) => void;
  setExecution: (execution: ExecutionResult | null) => void;
  resetRun: () => void;
}

export const useAgentsStore = create<AgentsState>()((set) => ({
  states: {
    context: idleAgentState("context"),
    solver: idleAgentState("solver"),
    reviewer: idleAgentState("reviewer"),
  },
  files: [],
  tokens: null,
  execution: null,

  setAgentState: (agent, patch) =>
    set((state) => ({
      states: { ...state.states, [agent]: { ...state.states[agent], ...patch, agent, updated_at: Date.now() } },
    })),

  setAgentsStatus: (statuses) =>
    set((state) => ({
      states: Object.fromEntries(
        AGENT_IDS.map((agent) => [
          agent,
          { ...state.states[agent], status: statuses[agent] ?? state.states[agent].status, updated_at: Date.now() },
        ]),
      ) as Record<AgentId, AgentState>,
    })),

  setFiles: (files) => set({ files }),
  setTokens: (tokens) => set({ tokens }),
  setExecution: (execution) => set({ execution }),

  resetRun: () =>
    set({
      states: {
        context: idleAgentState("context"),
        solver: idleAgentState("solver"),
        reviewer: idleAgentState("reviewer"),
      },
      files: [],
      tokens: null,
      execution: null,
    }),
}));

export function agentStatusLabel(status: string): string {
  switch (status) {
    case "idle":
      return "Idle";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}
