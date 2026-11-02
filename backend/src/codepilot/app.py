"""FastAPI application factory.

The app is built from injected settings so tests and deployments never rely on
import-time environment reads.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codepilot import __version__
from codepilot.api.errors import register_exception_handlers
from codepilot.api.middleware import CorrelationMiddleware
from codepilot.api.routers import health, providers, sessions
from codepilot.config.logging import configure_logging
from codepilot.config.settings import Environment, Settings
from codepilot.container import AppContainer

_DESCRIPTION = """
CodePilot AI is a multi-agent coding assistant with retrieval-augmented context.

This service exposes the backend consumed by the VS Code extension. The API is
versioned under `/v1`; breaking changes require a new version prefix.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured FastAPI application.

    Args:
        settings: Optional explicit settings. When omitted, settings are loaded
            from ``CODEPILOT_*`` environment variables and ``.env`` files.

    Returns:
        A fully wired application. All resources are created during startup and
        released during shutdown.
    """
    resolved = settings or Settings()
    docs_enabled = resolved.environment is not Environment.PRODUCTION

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(resolved.logging)
        container = AppContainer(resolved)
        app.state.container = container
        await container.startup()
        try:
            yield
        finally:
            await container.shutdown()
            app.state.container = None

    app = FastAPI(
        title=resolved.app_name,
        version=__version__,
        description=_DESCRIPTION,
        debug=resolved.debug,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Liveness and dependency readiness."},
            {"name": "providers", "description": "LLM provider configuration status."},
            {"name": "sessions", "description": "Chat sessions and messages."},
        ],
    )

    if resolved.server.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved.server.cors_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
            allow_credentials=False,
        )

    # Added last so that it wraps CORS and every request gets a correlation ID.
    app.add_middleware(CorrelationMiddleware, mask_unexpected_errors=not resolved.debug)

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(providers.router)
    app.include_router(sessions.router)
    return app
