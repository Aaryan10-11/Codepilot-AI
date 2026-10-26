"""Health endpoints over the ASGI transport."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from codepilot.api.deps import get_health_service
from codepilot.app import create_app
from codepilot.config.settings import Settings
from codepilot.services.health import HealthService
from tests.helpers import StubProbe


def _app(settings: Settings, service: HealthService) -> FastAPI:
    app = create_app(settings)
    app.dependency_overrides[get_health_service] = lambda: service
    return app


def _service(*probes: StubProbe) -> HealthService:
    return HealthService(probes=probes, version="9.9.9", environment="test")


async def test_liveness_reports_version(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings, _service(StubProbe("postgres")))

    async with client_factory(app) as client:
        response = await client.get("/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


async def test_health_snapshot_reports_every_component(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings, _service(StubProbe("postgres"), StubProbe("qdrant")))

    async with client_factory(app) as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["environment"] == "test"
    assert [component["name"] for component in payload["components"]] == ["postgres", "qdrant"]
    assert all(component["status"] == "up" for component in payload["components"])


async def test_health_snapshot_stays_200_when_dependencies_are_down(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(
        settings,
        _service(StubProbe("postgres", error=ConnectionError("refused"))),
    )

    async with client_factory(app) as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"


async def test_readiness_fails_with_503_when_required_dependency_is_down(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(
        settings,
        _service(
            StubProbe("postgres"),
            StubProbe("qdrant", error=ConnectionError("refused")),
        ),
    )

    async with client_factory(app) as client:
        response = await client.get("/v1/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["components"][1]["status"] == "down"


async def test_readiness_passes_when_all_dependencies_are_up(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings, _service(StubProbe("postgres"), StubProbe("qdrant")))

    async with client_factory(app) as client:
        response = await client.get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_optional_dependency_failure_is_degraded_but_ready(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(
        settings,
        _service(
            StubProbe("postgres"),
            StubProbe("telemetry", required=False, error=RuntimeError("offline")),
        ),
    )

    async with client_factory(app) as client:
        response = await client.get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


async def test_openapi_documents_health_endpoints(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = create_app(settings)

    async with client_factory(app) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/health" in paths
    assert "/v1/health/live" in paths
    assert "/v1/health/ready" in paths


@pytest.mark.parametrize("path", ["/v1/health", "/v1/health/ready"])
async def test_error_responses_are_not_returned_for_healthy_service(
    path: str,
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings, _service(StubProbe("postgres")))

    async with client_factory(app) as client:
        response = await client.get(path)

    assert response.status_code == 200
    assert "error" not in response.json()
