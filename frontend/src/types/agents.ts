import type { TokenUsage } from "./api";

export type { TokenUsage };

/** The three agents of the system, in the order the orchestration runs them. */
export const AGENT_IDS = ["context", "solver", "reviewer"] as const;

export type AgentId = (typeof AGENT_IDS)[number];

export type AgentStatus = "idle" | "running" | "completed" | "failed";

export interface AgentState {
  agent: AgentId;
  status: AgentStatus;
  phase?: string;
  detail?: string;
  updated_at: number;
}

export interface ContextFileRef {
  path: string;
  language: string;
  score?: number;
  preview?: string;
  status?: "pending" | "applied";
  content?: string;
}

export interface ContextSnapshot {
  files: ContextFileRef[];
  tokens: TokenUsage | null;
  detail?: string;
}

/** Complexity block attached to DSA solutions. */
export interface ComplexityReport {
  time_complexity: string;
  space_complexity: string;
  brute_force_time_complexity?: string;
}

export type ExecutionStatus = "idle" | "queued" | "running" | "passed" | "failed";

export interface ExecutionResult {
  status: ExecutionStatus;
  language?: string;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  duration_ms: number | null;
  tests: { passed: number; failed: number; total: number } | null;
}

export interface ReviewerFinding {
  severity: "critical" | "major" | "minor";
  file?: string;
  line?: number;
  message: string;
}

/** Normalized event stream consumed by the frontend run timeline. */
export type AgentRunEvent = {
  type: "context.status";
  status: AgentStatus;
  detail?: string;
} | {
  type: "context.files";
  files: ContextFileRef[];
} | {
  type: "context.tokens";
  tokens: TokenUsage;
} | {
  type: "solver.status";
  status: AgentStatus;
  phase?: string;
} | {
  type: "solver.delta";
  text: string;
} | {
  type: "solver.code";
  path: string;
  content: string;
  language: string;
  action: "create" | "update";
} | {
  type: "reviewer.status";
  status: AgentStatus;
} | {
  type: "reviewer.report";
  verdict: "approved" | "changes_requested" | "failed";
  findings: ReviewerFinding[];
  complexity: ComplexityReport;
} | {
  type: "execution.status";
  status: ExecutionStatus;
} | {
  type: "execution.log";
  stream: "stdout" | "stderr";
  line: string;
} | {
  type: "execution.result";
  result: ExecutionResult;
};

/** Inbound websocket frames the backend pushes for a running agent turn. */
export type AgentSocketFrame =
  | { kind: "agent_event"; event: AgentRunEvent }
  | { kind: "run.status"; status: "queued" | "running" | "completed" | "failed" }
  | { kind: "context.snapshot"; context: ContextSnapshot };
