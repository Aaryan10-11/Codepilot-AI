"""Error envelope mapping and request correlation."""

from __future__ import annotations

import re
from collections.abc import Callable

from fastapi import FastAPI
from httpx import AsyncClient

from codepilot.api.deps import get_health_service
from codepilot.app import create_app
from codepilot.config.settings import Settings
from codepilot.errors import DependencyUnavailableError
from codepilot.services.health import HealthService
from tests.helpers import StubProbe


def _app(settings: Settings) -> FastAPI:
    app = create_app(settings)

    @app.get("/_test/domain-error")
    async def _domain_error() -> None:
        raise DependencyUnavailableError(
            "Qdrant is unreachable",
            details={"component": "qdrant"},
        )

    @app.get("/_test/crash")
    async def _crash() -> None:
        raise RuntimeError("internal detail that must not leak")

    @app.get("/_test/validate")
    async def _validate(n: int) -> int:
        return n

    return app


async def test_domain_error_is_mapped_to_envelope(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)

    async with client_factory(app) as client:
        response = await client.get("/_test/domain-error")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"] == {
        "code": "dependency_unavailable",
        "message": "Qdrant is unreachable",
        "details": {"component": "qdrant"},
    }
    assert payload["request_id"] == response.headers["x-request-id"]


async def test_validation_error_lists_fields(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)

    async with client_factory(app) as client:
        response = await client.get("/_test/validate", params={"n": "abc"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["fields"][0]["location"] == "query.n"
    assert error["details"]["fields"][0]["type"] == "int_parsing"


async def test_unknown_route_returns_not_found_envelope(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)

    async with client_factory(app) as client:
        response = await client.get("/v1/does-not-exist")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"] == "Not Found"


async def test_method_not_allowed_uses_envelope(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)

    async with client_factory(app) as client:
        response = await client.post("/v1/health/live")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


async def test_unhandled_exception_is_masked(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)

    async with client_factory(app) as client:
        response = await client.get("/_test/crash")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "internal_error"
    assert payload["error"]["message"] == "An unexpected error occurred."
    assert "internal detail" not in response.text
    assert payload["request_id"] == response.headers["x-request-id"]


async def test_incoming_request_id_is_propagated(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)
    request_id = "client-trace-12345678"

    async with client_factory(app) as client:
        response = await client.get("/v1/health/live", headers={"X-Request-ID": request_id})

    assert response.headers["x-request-id"] == request_id


async def test_invalid_request_id_is_replaced(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(settings)

    async with client_factory(app) as client:
        response = await client.get("/v1/health/live", headers={"X-Request-ID": "short"})

    request_id = response.headers["x-request-id"]
    assert request_id != "short"
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


async def test_error_envelope_carries_request_id_from_middleware(
    settings: Settings,
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = create_app(settings)
    app.dependency_overrides[get_health_service] = lambda: HealthService(
        probes=[StubProbe("postgres")],
        version="1",
        environment="test",
    )

    async with client_factory(app) as client:
        response = await client.get("/v1/nope")

    payload = response.json()
    assert payload["request_id"] == response.headers["x-request-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", payload["request_id"])
