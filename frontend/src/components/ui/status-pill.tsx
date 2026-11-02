import type { AgentStatus, ExecutionStatus } from "../../types/agents";

interface StatusPillProps {
  status: AgentStatus | ExecutionStatus;
  label?: string;
}

const statusLabels: Record<string, string> = {
  idle: "Idle",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  queued: "Queued",
  passed: "Passed",
};

export function StatusPill({ status, label }: StatusPillProps) {
  const text = label ?? statusLabels[status] ?? status;
  return (
    <span className="status-pill" data-status={status}>
      <span className="dot" />
      {text}
    </span>
  );
}
