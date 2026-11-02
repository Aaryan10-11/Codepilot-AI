import { useState } from "react";
import { FolderGit2, FileCode, RefreshCw, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { StatusPill } from "../components/ui/status-pill";

interface FileNode {
  name: string;
  type: "file" | "dir";
  path: string;
  children?: FileNode[];
}

const PROJECT_TREE: FileNode[] = [
  {
    name: "backend",
    type: "dir",
    path: "backend",
    children: [
      {
        name: "src/codepilot",
        type: "dir",
        path: "backend/src/codepilot",
        children: [
          { name: "api/", type: "dir", path: "backend/src/codepilot/api" },
          { name: "llm/", type: "dir", path: "backend/src/codepilot/llm" },
          { name: "services/", type: "dir", path: "backend/src/codepilot/services" },
          { name: "container.py", type: "file", path: "backend/src/codepilot/container.py" },
          { name: "app.py", type: "file", path: "backend/src/codepilot/app.py" },
        ],
      },
    ],
  },
  {
    name: "frontend",
    type: "dir",
    path: "frontend",
    children: [
      { name: "src/", type: "dir", path: "frontend/src" },
      { name: "package.json", type: "file", path: "frontend/package.json" },
    ],
  },
  { name: "docker", type: "dir", path: "docker" },
  { name: "README.md", type: "file", path: "README.md" },
];

export function CodebasePage() {
  const [indexing, setIndexing] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string>("backend/src/codepilot/container.py");

  const handleIndex = () => {
    setIndexing(true);
    setTimeout(() => setIndexing(false), 1200);
  };

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between gap-4 pb-4">
        <div>
          <h1 className="text-title font-semibold tracking-tight">Codebase & RAG Index</h1>
          <p className="text-small text-muted">Tree-sitter parsing, hybrid vector embedding, and project structure</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleIndex} disabled={indexing}>
            <RefreshCw className={`h-3.5 w-3.5 ${indexing ? "animate-spin" : ""}`} />
            {indexing ? "Indexing..." : "Re-index Codebase"}
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-3">
        <Card className="flex flex-col overflow-hidden">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">File Explorer</CardTitle>
            <StatusPill status="completed" label="Indexed" />
          </CardHeader>
          <div className="min-h-0 flex-1 overflow-y-auto font-mono text-xs">
            <div className="flex flex-col gap-1 p-2">
              {PROJECT_TREE.map((node) => (
                <div key={node.path} className="flex flex-col gap-1">
                  <div
                    onClick={() => node.type === "file" && setSelectedFile(node.path)}
                    className={`flex items-center gap-2 rounded-[6px] px-2 py-1.5 cursor-pointer transition-colors ${
                      selectedFile === node.path ? "bg-raised text-text" : "text-muted hover:bg-raised hover:text-text"
                    }`}
                  >
                    <FolderGit2 className="h-4 w-4 text-accent shrink-0" />
                    <span>{node.name}</span>
                  </div>
                  {node.children?.map((child) => (
                    <div
                      key={child.path}
                      onClick={() => child.type === "file" && setSelectedFile(child.path)}
                      className={`ml-4 flex items-center gap-2 rounded-[6px] px-2 py-1.5 cursor-pointer transition-colors ${
                        selectedFile === child.path ? "bg-raised text-text" : "text-muted hover:bg-raised hover:text-text"
                      }`}
                    >
                      <FileCode className="h-3.5 w-3.5 text-positive shrink-0" />
                      <span>{child.name}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </Card>

        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card className="flex flex-col">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Vector DB & Indexing Status</CardTitle>
            </CardHeader>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-[6px] border border-border bg-ground p-3">
                <p className="text-xs text-muted">Vector Store</p>
                <p className="mt-1 text-sm font-semibold">Qdrant (Async)</p>
                <span className="mt-2 inline-flex items-center gap-1.5 text-xs text-positive">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Connected
                </span>
              </div>
              <div className="rounded-[6px] border border-border bg-ground p-3">
                <p className="text-xs text-muted">Indexed Files</p>
                <p className="mt-1 text-sm font-semibold">42 files</p>
                <span className="mt-2 text-xs text-muted">1,280 chunks</span>
              </div>
              <div className="rounded-[6px] border border-border bg-ground p-3">
                <p className="text-xs text-muted">Embedding Model</p>
                <p className="mt-1 text-sm font-semibold">text-embedding-3</p>
                <span className="mt-2 text-xs text-muted">1536 dims</span>
              </div>
            </div>
          </Card>

          <Card className="flex min-h-0 flex-1 flex-col">
            <CardHeader>
              <CardTitle className="text-sm font-semibold font-mono">{selectedFile}</CardTitle>
              <span className="text-xs text-muted">Preview</span>
            </CardHeader>
            <div className="min-h-0 flex-1 overflow-y-auto rounded-[6px] bg-ground p-4 font-mono text-xs leading-relaxed text-muted">
              <pre>
                {`# CodePilot AI Composition Root & Dependency Injection
from fastapi import FastAPI
from codepilot.config.settings import Settings
from codepilot.db.engine import create_db_engine
from codepilot.vector_db.client import create_vector_client

class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_engine = create_db_engine(settings.database)
        self.vector_client = create_vector_client(settings.vector_db)
`}
              </pre>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
