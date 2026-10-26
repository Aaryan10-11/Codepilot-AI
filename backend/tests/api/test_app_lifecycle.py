"""Application lifespan and container ownership."""

from __future__ import annotations

from collections.abc import Callable

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient

from codepilot.app import create_app
from codepilot.config.settings import Environment, Settings
from codepilot.container import AppContainer


async def test_lifespan_creates_and_releases_the_container(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = create_app(settings)

    async with LifespanManager(app):
        container = app.state.container
        assert isinstance(container, AppContainer)
        assert container.settings is settings

        async with client_factory(app) as client:
            response = await client.get("/v1/health/live")

        assert response.status_code == 200

    assert app.state.container is None


async def test_production_disables_documentation(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = create_app(Settings(environment=Environment.PRODUCTION, _env_file=None))

    async with client_factory(app) as client:
        docs = await client.get("/docs")
        openapi = await client.get("/openapi.json")

    assert docs.status_code == 404
    assert openapi.status_code == 404


async def test_cors_is_only_enabled_when_origins_are_configured(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = create_app(settings)

    async with client_factory(app) as client:
        response = await client.get(
            "/v1/health/live",
            headers={"Origin": "http://localhost:3000"},
        )

    assert "access-control-allow-origin" not in response.headers
