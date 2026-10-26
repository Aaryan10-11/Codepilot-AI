# ADR 0001 — Foundation decisions

- **Status:** accepted
- **Date:** 2026-10-26
- **Milestone:** 0

## Context

We need a backend skeleton that will still be credible once four providers, three
agents, a retrieval pipeline, and a sandbox are added. The skeleton must be
testable without external services, enforce module boundaries, and avoid the
usual FastAPI pitfalls (import-time config, global clients, ad-hoc error
handling).

## Decisions

### 1. uv with a `src/` layout, Python pinned to 3.12

uv gives a real lockfile, fast installs in Docker and CI, and PEP 735 dependency
groups. The `src/` layout prevents accidental imports of the working tree and is
standard for installable packages.

### 2. A hand-written typed container instead of a DI framework

`AppContainer` wires clients explicitly in one file. A framework would hide the
wiring without eliminating it. Constructor injection keeps every dependency
visible, and FastAPI dependency overrides handle test substitution.

### 3. Nested pydantic-settings with `__` as the nesting delimiter

`CODEPILOT_DATABASE__URL` is readable in Compose and unambiguous. Config models
are small per subsystem, validated at startup, and passed down as objects.
Production-only safety checks (no wildcard CORS, no debug) live in a model
validator rather than in deployment docs.

### 4. Pure ASGI middleware for correlation and error masking

`BaseHTTPMiddleware` interacts badly with context variables and streaming, both
of which matter for SSE. Starlette's `ServerErrorMiddleware` sits outside all
user middleware, so a generic `Exception` handler renders 500s without our
correlation header. The correlation middleware therefore converts unhandled
exceptions into the public envelope itself (unless debug is enabled), and the
generic handler remains as a last-resort fallback.

### 5. Three health endpoints with different contracts

- `/v1/health/live` never probes dependencies: a restart will not fix Postgres.
- `/v1/health/ready` returns 503 when a required dependency is down.
- `/v1/health` always returns 200 with per-component detail for dashboards.

Probes run concurrently under a per-probe deadline, and error text is scrubbed of
URL credentials and truncated. A failing probe can never crash the report.

### 6. Pin infrastructure images, keep development compose minimal

Qdrant is pinned to `v1.20.0` to match the client major/minor and avoid
compatibility surprises. PostgreSQL is pinned to 16. The backend image is
multi-stage, runs as a non-root user, and installs from the lockfile only.

### 7. Quality gates are part of the definition of done

`ruff`, `ruff format`, strict `mypy`, `import-linter`, and `pytest` with a 90%
coverage floor run in CI for every milestone. Architecture contracts are code,
not review comments.

## Consequences

- Adding a provider requires an adapter plus a registry entry, not edits to
  agents.
- Tests remain fast and offline; integration tests arrive with Testcontainers in
  Milestone 4.
- The container grows with the project; if wiring exceeds ~150 lines it should be
  split per subsystem with a shared resource registry.
- SSE/WebSocket work will extend the existing pure-ASGI middleware rather than
  replacing it.
