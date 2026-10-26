"""Shared test fixtures.

Unit tests never touch real infrastructure; API tests run in-process against
the ASGI app with dependencies overridden.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from codepilot.config.settings import Environment, LoggingSettings, Settings


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent developer/CI environment variables from leaking into tests."""
    for name in list(os.environ):
        if name.startswith("CODEPILOT_"):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    """Keep global structlog configuration from leaking between tests."""
    yield
    structlog.reset_defaults()


@pytest.fixture
def settings() -> Settings:
    """Deterministic settings that do not read any ``.env`` file."""
    return Settings(
        environment=Environment.TEST,
        debug=False,
        logging=LoggingSettings(level="CRITICAL", format="json"),
        _env_file=None,
    )


@pytest.fixture
def client_factory() -> Callable[[FastAPI], AsyncClient]:
    """Build an in-process HTTP client for a FastAPI app."""

    def factory(app: FastAPI) -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        )

    return factory
