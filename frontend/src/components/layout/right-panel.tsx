import { Bot, Brain, Database, FileText, PlaySquare, Terminal } from "lucide-react";
import { StatusPill } from "../ui/status-pill";
import { Card, CardHeader, CardTitle } from "../ui/card";
import { useAgentsStore } from "../../stores/agents";

export function RightPanel() {
  const agents = useAgentsStore((state) => state.states);
  const files = useAgentsStore((state) => state.files);

  return (
    <aside className="context-panel" aria-label="AI Intelligence Panel">
      {/* Active Agents */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Active Agents</CardTitle>
        </CardHeader>
        {[
          { name: "Context Agent", icon: Brain, status: agents.context.status, desc: "Retrieves workspace context" },
          { name: "Solver Agent", icon: PlaySquare, status: agents.solver.status, desc: "Generates solutions" },
          { name: "Reviewer Agent", icon: Bot, status: agents.reviewer.status, desc: "Verifies quality" },
        ].map((agent) => (
          <div key={agent.name} className="mb-3 flex items-start gap-3 rounded-[8px] border border-border bg-ground p-3">
            <agent.icon className="h-4 w-4 text-accent mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-text">{agent.name}</p>
                <StatusPill status={agent.status} />
              </div>
              <p className="text-[11px] text-muted mt-1">{agent.desc}</p>
            </div>
          </div>
        ))}
      </Card>

      {/* Context */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Context Panel</CardTitle>
        </CardHeader>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs text-muted">Retrieved files</span>
          <span className="text-xs font-mono">{files.length}</span>
        </div>
        {files.length > 0 ? (
          <ul className="max-h-[140px] space-y-1 overflow-auto pr-1 text-[11px]">
            {files.slice(0, 6).map((file) => (
              <li key={file.path} className="flex items-center justify-between rounded-[6px] bg-ground px-2 py-1">
                <span className="truncate font-mono text-text">{file.path}</span>
                <span className="text-[10px] text-muted">{file.score?.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted">No context retrieved yet.</p>
        )}
        <button className="mt-2 w-full rounded-[6px] border border-border py-1.5 text-xs text-muted hover:bg-raised hover:text-text">
          View all
        </button>
      </Card>

      {/* Tools */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Tools</CardTitle>
        </CardHeader>
        <div className="grid grid-cols-2 gap-2">
          {[
            { icon: FileText, name: "Read" },
            { icon: Database, name: "Write" },
            { icon: PlaySquare, name: "Search" },
            { icon: Terminal, name: "Run" },
          ].map((tool) => (
            <div key={tool.name} className="flex items-center gap-2 rounded-[6px] border border-border bg-ground px-2 py-1.5">
              <tool.icon className="h-3.5 w-3.5 text-muted" />
              <span className="text-[11px] text-text">{tool.name}</span>
              <span className="ml-auto text-[10px] text-positive">Ready</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Project */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Project</CardTitle>
        </CardHeader>
        <div className="text-xs space-y-2">
          <div className="flex justify-between">
            <span className="text-muted">Name</span>
            <span className="font-mono text-text">CodePilotAI</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">Indexed files</span>
            <span className="font-mono text-text">42</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">RAG status</span>
            <StatusPill status="completed" />
          </div>
        </div>
      </Card>
    </aside>
  );
}
