# Architecture

This document is the working design for CodePilot AI. Milestone 0 status is
called out explicitly; everything else is the committed target design.

## 1. Layering

```
api  →  services  →  agents  →  tools / rag  →  infra
                        ↓                        (llm, db, vector_db,
                      models                       execution, parser)
```

Rules:

- Dependencies point inward only.
- `models` import nothing from the project.
- Vendor SDK types never leave `llm/providers/*` (or `embeddings/providers/*`).
- `agents` never import `api`; `tools` and `rag` never import `agents`.
- CI enforces these boundaries with `import-linter`.

Cross-cutting concerns (logging, config, error types) are injected as small
objects through constructors. There is no import-time environment read and no
module-level singleton.

## 2. Composition root

`AppContainer` is created in the FastAPI lifespan, owns every process-scoped
resource, and releases them on shutdown. Handlers receive services through
FastAPI dependencies that read `app.state.container`.

This is deliberate: a DI framework would add indirection without removing the
wiring code, and the container is small enough to read in one screen.

## 3. Domain contracts

| Contract | Responsibility |
|---|---|
| `LLMProvider` | `complete`, `stream`, tool calls, usage, capabilities |
| `EmbeddingProvider` | `embed_documents`, `embed_query`, dimensions, model id |
| `VectorStore` | collection lifecycle, upsert, delete-by-filter, hybrid search |
| `CodeParser` | language detection, parse into symbols/spans |
| `Tool` | name, description, input model, risk class, async `execute` |
| `SandboxExecutor` | run a program under limits, return structured output |
| `Retriever` / `Reranker` | recall then precision over indexed chunks |
| `Agent` | `run(task, context) -> structured result` |
| `ConversationStore` / `RunStore` | persistence and replay |

Every contract has an in-memory or fake implementation used by unit tests.

## 4. Request lifecycle

```
request
  └─ Context Agent        (read-only tools)      → ContextBundle
       └─ Solver Agent    (read/write tools)     → patch + explanation
            └─ Reviewer   (read-only tools)     → ReviewResult
                 └─ execute in sandbox          → ExecutionResult
                      ├─ pass  → return artifacts
                      └─ fail  → Solver (max 2 fixes) → Reviewer → execute
```

Budgets are enforced by the orchestrator, not by prompts:

- `max_tool_iterations` per agent pass
- `max_fix_iterations`
- token budget per phase and per run
- hard `max_cost_usd` per run
- wall-clock deadline
- cooperative cancellation via `CancellationToken`

Reviewer capability is restricted by tool registry, not instructions. The
Reviewer may execute code to verify claims but can never write files.

## 5. Indexing

Supported extensions: `.py .cpp .hpp .java .ts .tsx .js .jsx .md .json .yaml .yml`.

1. `ripgrep --json` discovery honouring `.gitignore` and hard excludes.
2. Content hash (BLAKE3/sha256) compared against `indexed_files`.
   Unchanged files are skipped entirely.
3. Tree-sitter parse → symbol-aware chunks with `symbol_path` and line ranges.
   Oversized symbols split with overlap; tiny siblings merge.
4. Batch embeddings → upsert to Qdrant with full payload.
5. Manifest row written only after a successful upsert, so crashes cause a
   re-index rather than a silent gap.

Parsing is CPU-bound and runs in a bounded process pool.

## 6. Retrieval

```
query → planner (intent + filters + expansions)
      → dense search ∥ lexical search
      → reciprocal rank fusion
      → rerank
      → token-budgeted packer (per-file, per-chunk, adjacent expansion)
      → ContextBundle with citations
```

Hard filter on `workspace_id` for every query. Retrieval is evaluated against
golden fixtures (recall@k gate) so prompt or chunker changes cannot silently
degrade quality.

## 7. Persistence

PostgreSQL owns canonical state: workspaces, index runs, indexed files, chunks,
conversations, messages, runs, run events, artifacts, solutions, summaries,
usage ledger.

Qdrant owns only embeddings plus filterable payload. Deletes use filters on
`rel_path`/`content_hash`; no in-memory ID bookkeeping.

`run_events` is append-only with a monotonic `seq`, which makes SSE streams
resumable via `Last-Event-ID`.

## 8. Execution sandbox

One container per execution, pre-baked toolchain images pinned by digest:

- `--network none`, read-only root filesystem, tmpfs `/tmp`
- non-root UID, memory/CPU/PID limits, wall-clock timeout, output caps
- workspace mounted read-only; only an output directory is writable
- no package installation at runtime

The executor returns typed results (`exit_code`, `stdout`, `stderr`, `timed_out`,
`oom_killed`, `duration_ms`) rather than raising on user-code failure.

## 9. Security model

- Single workspace jail function resolves and validates every path, including
  symlink realpaths. Every filesystem tool goes through it.
- Tool risk classes (`READ`, `WRITE`, `EXECUTE`, `DESTRUCTIVE`) drive approval
  and audit logging.
- Secrets are read from environment variables only and redacted in logs before
  rendering.
- No file contents or prompts in logs at `INFO`.
- Error responses never include stack traces or internal identifiers.

## 10. Observability

- structlog JSON in containers; request/run correlation IDs on every line.
- OpenTelemetry spans per phase, tool call, and provider call (Milestone 8).
- Prometheus counters/histograms for tokens, cost, latency, tool errors, and
  fix-loop rate.
- `/v1/health` for humans, `/v1/health/ready` for orchestrators.

## 11. Testing strategy

| Layer | Technique |
|---|---|
| Unit | fakes only; no network, database, or Docker |
| Contract | shared suite per provider/store/tool implementation |
| Integration | Testcontainers for Postgres, Qdrant, sandbox |
| Retrieval | golden queries with recall@k thresholds |
| E2E | full run against a deterministic fake provider |
| Evaluation | per-agent scenario suite, run on model/prompt changes |

## 12. Current state (Milestone 0)

Implemented:

- configuration and validation, structured logging with redaction
- container and dependency wiring
- PostgreSQL/Qdrant connection ownership and readiness probes
- request correlation middleware and the error envelope
- health endpoints, Docker images/compose, CI with lint, types, tests, imports

Not yet implemented: everything in sections 3–11 beyond the contracts listed as
target design. The next milestone is the provider-neutral LLM layer.

## 13. Open decisions

1. Hybrid lexical search: Qdrant sparse vectors vs PostgreSQL FTS.
2. Target repository scale (affects chunking and rerank strategy).
3. Windows path and bind-mount performance guarantees.
4. Whether to ship local-model (Ollama) support.
5. Single-user local mode vs multi-tenant SaaS isolation.
6. Default per-request cost ceiling.
