import { useAgentsStore } from "../../stores/agents";
import { useSettingsStore } from "../../stores/settings";
import { StatusPill } from "../ui/status-pill";
import { Card, CardHeader, CardTitle } from "../ui/card";
import type { AgentStatus, ExecutionStatus } from "../../types/agents";

function AgentCard({
  name,
  phase,
  detail,
  status,
}: {
  name: string;
  phase?: string;
  detail?: string;
  status: AgentStatus | ExecutionStatus;
}) {
  return (
    <Card className="mb-3">
      <CardHeader>
        <CardTitle className="text-sm font-semibold">{name}</CardTitle>
        <StatusPill status={status} />
      </CardHeader>
      {phase ? <p className="text-xs text-muted">{phase}</p> : null}
      {detail ? <p className="mt-1 text-xs text-muted">{detail}</p> : null}
    </Card>
  );
}

export function ContextPanel() {
  const agents = useAgentsStore((state) => state);
  const settings = useSettingsStore((state) => state);

  const activeFiles = agents.files;

  return (
    <aside className="context-panel" aria-label="Agent context panel">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Context</h2>
        <StatusPill status={agents.states.context.status} />
      </div>

      <AgentCard name="Context Agent" phase="Retrieving workspace context" status={agents.states.context.status} detail={agents.states.context.detail} />

      <div className="mb-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-muted">Retrieved files</h3>
          <span className="text-xs text-muted">{activeFiles.length}</span>
        </div>
        {activeFiles.length === 0 ? (
          <p className="text-xs text-muted">No files retrieved yet this run.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {activeFiles.map((file) => (
              <li key={file.path} className="rounded-[6px] border border-border bg-surface px-2 py-1.5">
                <span className="font-mono text-xs text-text">{file.path}</span>
                {typeof file.score === "number" ? <span className="ml-2 text-[10px] text-muted">score {file.score.toFixed(2)}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <AgentCard name="Solver Agent" phase="Solving" status={agents.states.solver.status} detail={agents.states.solver.detail} />

      <AgentCard
        name="Reviewer Agent"
        phase="Reviewing"
        status={agents.states.reviewer.status}
        detail={agents.states.reviewer.detail}
      />

      <div className="mt-6 border-t border-rule pt-4">
        <h3 className="mb-2 text-xs font-semibold text-muted">Run</h3>
        {agents.execution ? (
          <div className="flex flex-col gap-2">
            <StatusPill status={agents.execution.status} />
            {agents.tokens ? (
              <p className="text-xs text-muted">
                Tokens · in {agents.tokens.input_tokens.toLocaleString()} · out {agents.tokens.output_tokens.toLocaleString()}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="text-xs text-muted">Execution has not run yet in this session.</p>
        )}
      </div>

      <div className="mt-4 border-t border-rule pt-4">
        <h3 className="mb-2 text-xs font-semibold text-muted">Models</h3>
        <p className="text-xs text-muted">
          Solver <span className="font-mono">{settings.models.solver}</span>
        </p>
        <p className="text-xs text-muted">
          Reviewer <span className="font-mono">{settings.models.reviewer}</span>
        </p>
        <p className="text-xs text-muted">
          Context <span className="font-mono">{settings.models.context}</span>
        </p>
      </div>
    </aside>
  );
}
