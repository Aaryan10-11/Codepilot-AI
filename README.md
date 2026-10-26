# CodePilot AI

A production-oriented AI coding agent for DSA solving, debugging, code generation,
and codebase understanding — with a FastAPI backend, retrieval-augmented context,
three cooperating agents, and a VS Code extension.

> **Status: Milestone 0 complete.** The foundation boots, reports dependency
> health, and is covered by tests, strict typing, and architecture contracts.
> The agents, RAG pipeline, sandbox, and extension land in later milestones
> (see [Roadmap](#roadmap)).

---

## Why this exists

Most "AI coding" demos send an entire repository to one model and hope. CodePilot
AI is built around three ideas instead:

1. **Context is retrieved, not dumped.** Tree-sitter chunking plus hybrid search
   puts only relevant code in front of the model, with citations.
2. **Writing and reviewing are separate capabilities.** The Reviewer has a
   read-only tool registry — it cannot implement, only verify.
3. **Every layer is replaceable.** Providers, vector stores, embeddings, tools,
   and sandboxes sit behind protocols; nothing vendor-specific leaks into
   agents or domain models.

---

## Architecture

```
                       ┌──────────────────────────────┐
   VS Code extension ──▶│  FastAPI  /v1  (SSE/WS)      │
                       └──────────────┬───────────────┘
                                      │
                              ┌───────▼────────┐
                              │  Orchestrator  │  budgets · fix loop
                              └───┬────┬───┬───┘
                     ┌────────────┘    │   └────────────┐
                     ▼                 ▼                ▼
              ┌────────────┐   ┌────────────┐   ┌────────────┐
              │  Context   │   │   Solver   │   │  Reviewer  │
              │  read-only │   │ writes code│   │ read-only  │
              └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
                    │                │                │
                    ▼                ▼                ▼
              ┌────────────────────────────────────────────┐
              │  Tool registry  (sandboxed, audited)       │
              │  files · search · git · terminal · sandbox │
              └────────────────────────────────────────────┘
                    │
      ┌─────────────┼──────────────┬───────────────┐
      ▼             ▼              ▼               ▼
  PostgreSQL      Qdrant        LLM provider     Docker
  (state)      (embeddings)     adapters        (execution)
```

**Request flow:** `context → solve → review → execute → verify`, with a bounded
fix loop (`max 2` iterations by default) and hard token / cost / wall-clock
budgets. Every exit path returns a partial result instead of an exception.

Detailed design: [`docs/architecture.md`](docs/architecture.md).
Decisions: [`docs/adr/`](docs/adr/).

---

## Repository layout

```
backend/
  src/codepilot/
    api/            routers, schemas, dependencies, middleware, error mapping
    config/         pydantic-settings models, structured logging
    container.py    composition root (DI without globals)
    db/             async SQLAlchemy engine
    vector_db/      async Qdrant client
    models/         pure domain models
    services/       transport-agnostic use cases (health today)
    errors.py       typed exception hierarchy
  tests/            unit + in-process API tests
docker/
  compose.yaml      PostgreSQL + Qdrant + backend
  backend.Dockerfile
frontend/           VS Code extension (Milestone 10)
docs/               architecture and ADRs
```

Later milestones add `agents/`, `llm/`, `rag/`, `embeddings/`, `parser/`,
`tools/`, `execution/`, `memory/`, and `prompts/` at the same level — each with a
single responsibility and an explicit interface.

---

## Quick start

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12 (managed by uv) |
| [uv](https://docs.astral.sh/uv/) | 0.11+ |
| Docker + Compose | 29+ / v2 |

### 1. Configure

```bash
cp .env.example .env
```

Defaults are safe for local development and match `docker/compose.yaml`.

### 2. Start infrastructure

```bash
docker compose --env-file .env -f docker/compose.yaml up -d postgres qdrant
```

`--env-file .env` lets Compose read `POSTGRES_PORT` and the credentials from the
same file the backend uses. If a native PostgreSQL service already listens on
`5432`, set `POSTGRES_PORT=55432` in `.env` and update
`CODEPILOT_DATABASE__URL` to match. The backend container always reaches
PostgreSQL on the internal port `5432`.

### 3. Run the backend

```bash
cd backend
uv sync --all-groups
uv run uvicorn codepilot.app:create_app --factory --reload
```

The API is now at `http://127.0.0.1:8000` with interactive docs at `/docs`.

```bash
curl http://127.0.0.1:8000/v1/health
curl -i http://127.0.0.1:8000/v1/health/ready
```

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "checked_at": "2026-10-26T06:12:44.103Z",
  "uptime_seconds": 4.2,
  "components": [
    { "name": "postgres", "status": "up", "required": true, "latency_ms": 3.1, "detail": null },
    { "name": "qdrant",   "status": "up", "required": true, "latency_ms": 2.4, "detail": null }
  ]
}
```

### Full stack in Docker

```bash
cp .env.example .env
docker compose --env-file .env -f docker/compose.yaml up --build
```

The backend image runs as a non-root user, uses a locked dependency set, and
exposes a container health check.

### Tests and quality gates

```bash
cd backend
uv run pytest --cov=codepilot --cov-report=term-missing
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports
```

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `password authentication failed for user "codepilot"` | A native PostgreSQL on `5432` is answering instead of the container | Set `POSTGRES_PORT=55432` in `.env`, update `CODEPILOT_DATABASE__URL`, then `docker compose --env-file .env -f docker/compose.yaml up -d postgres` |
| Qdrant reports `timed out after 2s` | Qdrant container not running | `docker compose --env-file .env -f docker/compose.yaml up -d qdrant` |
| `uv sync` stalls on a cache lock | A previous uv process is still running | Close stale `uv`/`python` processes and retry |

---

## API conventions

- All routes are versioned under `/v1`.
- Every response carries `X-Request-ID`; a client-supplied ID is honoured when
  it matches `[A-Za-z0-9._-]{8,64}`, otherwise a new one is generated.
- Failures always use one envelope:

```json
{
  "error": {
    "code": "dependency_unavailable",
    "message": "Qdrant is unreachable",
    "details": { "component": "qdrant" }
  },
  "request_id": "7f1c..."
}
```

- `/v1/health` always returns `200` for dashboards; `/v1/health/ready` returns
  `503` when a required dependency is down; `/v1/health/live` probes nothing.

| Endpoint | Purpose |
|---|---|
| `GET /v1/health/live` | Process liveness |
| `GET /v1/health/ready` | Readiness (503 on required dependency failure) |
| `GET /v1/health` | Full component snapshot |
| `GET /docs` | OpenAPI UI (disabled in production) |

---

## Configuration

Configuration is layered: environment variables override `.env` files.
Nested keys use a double underscore.

| Variable | Default | Notes |
|---|---|---|
| `CODEPILOT_ENVIRONMENT` | `development` | `development` \| `test` \| `production` |
| `CODEPILOT_DEBUG` | `false` | Debug tracebacks; forbidden in production |
| `CODEPILOT_SERVER__PORT` | `8000` | |
| `CODEPILOT_SERVER__CORS_ORIGINS` | `[]` | JSON list; wildcard forbidden in production |
| `CODEPILOT_SERVER__HEALTH_TIMEOUT_SECONDS` | `2` | Per-probe deadline |
| `CODEPILOT_DATABASE__URL` | local Postgres | Must use `postgresql+asyncpg://` |
| `CODEPILOT_DATABASE__POOL_SIZE` | `10` | |
| `CODEPILOT_VECTOR_DB__URL` | `http://localhost:6333` | |
| `CODEPILOT_VECTOR_DB__API_KEY` | unset | Secret |
| `CODEPILOT_LOGGING__LEVEL` | `INFO` | |
| `CODEPILOT_LOGGING__FORMAT` | `console` | `console` \| `json` |
| `POSTGRES_PORT` | `5432` | Host port mapped by Compose; change if 5432 is taken |

Provider API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …) are introduced in
Milestone 1 and read by their adapters only.

---

## Roadmap

| # | Milestone | State |
|---|---|---|
| **M0** | Foundation: config, logging, DI, health, Docker, CI | **Done** |
| M1 | LLM abstraction: OpenAI, Anthropic, Gemini, DeepSeek, streaming, retries | Next |
| M2 | Tool layer: sandboxed file/search/git tools, approvals, audit log | Planned |
| M3 | Docker execution sandbox for Python, C++, Java | Planned |
| M4 | Tree-sitter parsing, incremental indexing, embeddings, Qdrant | Planned |
| M5 | Hybrid retrieval, reranking, token-budgeted context packing | Planned |
| M6 | Context, Solver, and Reviewer agents + bounded orchestration | Planned |
| M7 | PostgreSQL persistence, memory, past-run retrieval | Planned |
| M8 | Chat/SSE/WebSocket API, auth, tracing | Planned |
| M9 | DSA pipeline: 8-part solutions, judge, knowledge base | Planned |
| M10 | VS Code extension: chat, diff apply, indexing | Planned |
| M11 | Hardening: E2E, load, security, eval harness | Planned |

Each milestone leaves the project runnable with all quality gates passing.

---

## Engineering principles

- **No globals.** One `AppContainer` is created during lifespan and injected.
- **Typed boundaries.** Strict mypy; vendor SDK types stay inside adapters.
- **Async first.** CPU-bound parsing runs off the event loop, never inside it.
- **Fail loud, fail safe.** Typed exceptions map to a single envelope; internals
  never leak; health checks time out instead of hanging.
- **Tests earn their keep.** 92% branch coverage at M0; fakes for every external
  system so unit tests need no network or Docker.
- **Architecture is enforced.** `import-linter` contracts fail CI when layer
  boundaries are crossed.

---

## License

License to be selected before the first public release.
