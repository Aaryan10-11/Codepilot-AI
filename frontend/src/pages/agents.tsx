import { useState } from "react";
import { Bot, CheckCircle2, Settings2, Zap } from "lucide-react";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { StatusPill } from "../components/ui/status-pill";
import { Button } from "../components/ui/button";
import { useAgentsStore } from "../stores/agents";
import { useSettingsStore } from "../stores/settings";

interface AgentDef {
  id: string;
  name: string;
  role: string;
  description: string;
  model: string;
  enabled: boolean;
  status: "idle" | "running" | "completed" | "failed";
}

export function AgentStudioPage() {
  const agentStates = useAgentsStore((state) => state.states);
  const models = useSettingsStore((state) => state.models);

  const [agents, setAgents] = useState<AgentDef[]>([
    {
      id: "context",
      name: "Context Agent",
      role: "Retrieval & Symbol Indexing",
      description: "Retrieves relevant files, tree-sitter symbols, and RAG context snippets.",
      model: models.context,
      enabled: true,
      status: agentStates.context.status,
    },
    {
      id: "solver",
      name: "Solver Agent",
      role: "Code Generation & Implementation",
      description: "Generates robust solutions, writes code, and executes bounded fix loops.",
      model: models.solver,
      enabled: true,
      status: agentStates.solver.status,
    },
    {
      id: "reviewer",
      name: "Reviewer Agent",
      role: "Code Verification & Quality",
      description: "Read-only verification agent checking correctness, complexity, and security.",
      model: models.reviewer,
      enabled: true,
      status: agentStates.reviewer.status,
    },
  ]);

  const toggleAgent = (id: string) => {
    setAgents((prev) => prev.map((a) => (a.id === id ? { ...a, enabled: !a.enabled } : a)));
  };

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between gap-4 pb-4">
        <div>
          <h1 className="text-title font-semibold tracking-tight">Agent Studio</h1>
          <p className="text-small text-muted">Configure multi-agent coordination, models, and execution parameters</p>
        </div>
        <Button variant="secondary" size="sm">
          <Zap className="h-3.5 w-3.5 text-accent" />
          Run Orchestration Test
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto pb-4">
        <div className="grid gap-6 md:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id} className="flex flex-col justify-between">
              <div>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-raised text-accent">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold">{agent.name}</CardTitle>
                      <p className="text-xs text-muted">{agent.role}</p>
                    </div>
                  </div>
                  <StatusPill status={agent.status} />
                </CardHeader>
                <p className="mt-2 text-xs text-muted leading-relaxed">{agent.description}</p>
              </div>

              <div className="mt-6 flex flex-col gap-3 border-t border-rule pt-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Model</span>
                  <span className="font-mono text-text">{agent.model}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">State</span>
                  <span className="capitalize text-text">{agent.enabled ? "Active" : "Disabled"}</span>
                </div>
                <div className="flex items-center justify-between pt-2">
                  <Button variant="secondary" size="sm" onClick={() => toggleAgent(agent.id)}>
                    <Settings2 className="h-3.5 w-3.5" />
                    {agent.enabled ? "Disable" : "Enable"}
                  </Button>
                  <span className="text-[10px] text-muted font-mono">ID: {agent.id}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Orchestration Parameters</CardTitle>
            </CardHeader>
            <dl className="flex flex-col gap-3 text-sm">
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <dt className="text-muted">Max Fix Iterations</dt>
                <dd className="font-mono">2</dd>
              </div>
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <dt className="text-muted">Timeout per Agent</dt>
                <dd className="font-mono">45s</dd>
              </div>
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <dt className="text-muted">RAG Retrieval Top-K</dt>
                <dd className="font-mono">8</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-muted">Execution Sandbox</dt>
                <dd className="text-positive font-medium">Docker (Isolated)</dd>
              </div>
            </dl>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Execution History</CardTitle>
            </CardHeader>
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between rounded-[6px] border border-border bg-ground p-3 text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-positive" />
                  <div>
                    <p className="font-medium">Two Sum Python Optimization</p>
                    <p className="text-[10px] text-muted">Context → Solver → Reviewer · 342ms</p>
                  </div>
                </div>
                <span className="font-mono text-muted">2 mins ago</span>
              </div>
              <div className="flex items-center justify-between rounded-[6px] border border-border bg-ground p-3 text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-positive" />
                  <div>
                    <p className="font-medium">FastAPI Router Error Envelope</p>
                    <p className="text-[10px] text-muted">Context → Solver → Reviewer · 890ms</p>
                  </div>
                </div>
                <span className="font-mono text-muted">15 mins ago</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
