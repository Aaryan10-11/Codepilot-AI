# CodePilot AI — Frontend

The React + TypeScript web client for CodePilot AI. Built with Vite, React 19, TypeScript,
Tailwind CSS v4, Lucide icons, Monaco Editor, Zustand, Framer Motion and `react-markdown`.

## Stack

| Concern | Choice |
|---|---|
| UI library | React 19 + TypeScript (strict) |
| Build tool | Vite 6 |
| Styling | Tailwind CSS v4 (design tokens in `src/styles/index.css`) |
| State | Zustand (persisted UI, chat, agents, settings) |
| Editor | Monaco (`@monaco-editor/react`) |
| Markdown | `react-markdown` + `remark-gfm` + Prism syntax highlighting |
| Motion | Framer Motion (subtle entrances only) |
| Routing | React Router v6 |

## Getting started

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on <http://localhost:5173>. It proxies `/v1` and `/ws` to the FastAPI
backend on `127.0.0.1:8000` (see `vite.config.ts`).

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/v1` | REST base path |
| `VITE_WS_URL` | `ws://127.0.0.1:8000` | WebSocket base for agent events |

## Commands

```bash
npm run dev       # dev server
npm run build     # production build
npm run preview   # serve the production build
npm run typecheck # tsc --noEmit
```

## Structure

```
src/
  components/
    ui/         design-system primitives (button, inputs, card, status pill, switch, skeleton, empty state)
    layout/    app shell, sidebar, context panel
    chat/       markdown renderer, code blocks, composer, message list, welcome screen
    editor/    Monaco wrapper
    dsa/        DSA workspace components (execution panel, problem panel)
  pages/        workspace (chat), dsa, settings, not-found
  services/    API client, health, providers, chat, RAG context, execution, agent websocket
  stores/       zustand stores (ui, chat, agents, settings)
  types/        backend API / agent event / chat / RAG / DSA contracts
  styles/      design tokens, base styles, markdown and code-block styles
```

## Design system

Dark-first by default; an optional light theme is driven by `data-theme` on `<html>`.

- Ground `#171719`, surface `#131217`, raised `#212023`, border `#222224`, text `#ffffff`, muted `#8a8c92`, accent `#4a8ad6`.
- Type: Public Sans for UI text, JetBrains Mono for figures and code.
- Radius: card `6px`, controls fully rounded (pill).
- The one accent is reserved for selection/focus marks; actions use inversion (white on dark).

See `src/styles/index.css` for the full token set and `references/app-screens.md` in the
design skill for the underlying rules.

## Backend contract notes

The frontend consumes the backend contracts from `backend/src/codepilot`:

- `GET /v1/health`, `GET /v1/health/ready`, `GET /v1/health/live`
- `GET /v1/providers`, `POST /v1/providers/{id}/verify`
- Agent events over WebSocket frames shaped as `AgentRunEvent` (context → solver → reviewer → execution).
- Retrieval: `GET /v1/context/retrieve?query=&top_k=`

The frontend never stores API keys and never renders secrets.
