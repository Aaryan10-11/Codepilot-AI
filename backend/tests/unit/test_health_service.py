"""Health aggregation behaviour."""

from __future__ import annotations

import time

import pytest

from codepilot.models.health import ComponentStatus, OverallStatus
from codepilot.services.health import HealthService, PostgresProbe, QdrantProbe
from tests.helpers import StubPingable, StubProbe


def _service(*probes: StubProbe, timeout: float = 1.0) -> HealthService:
    return HealthService(
        probes=probes,
        version="9.9.9",
        environment="test",
        timeout_seconds=timeout,
    )


async def test_all_probes_up() -> None:
    report = await _service(
        StubProbe("postgres"),
        StubProbe("qdrant"),
    ).check()

    assert report.status is OverallStatus.OK
    assert report.version == "9.9.9"
    assert report.environment == "test"
    assert report.uptime_seconds >= 0
    assert [component.name for component in report.components] == ["postgres", "qdrant"]
    assert all(c.status is ComponentStatus.UP for c in report.components)
    assert all(c.latency_ms >= 0 for c in report.components)


async def test_required_probe_down_marks_service_unavailable() -> None:
    report = await _service(
        StubProbe("postgres"),
        StubProbe("qdrant", error=ConnectionError("connection refused")),
    ).check()

    assert report.status is OverallStatus.UNAVAILABLE
    qdrant = report.components[1]
    assert qdrant.status is ComponentStatus.DOWN
    assert qdrant.detail is not None
    assert "ConnectionError" in qdrant.detail


async def test_optional_probe_down_degrades_service() -> None:
    report = await _service(
        StubProbe("postgres"),
        StubProbe("telemetry", required=False, error=RuntimeError("not configured")),
    ).check()

    assert report.status is OverallStatus.DEGRADED
    assert report.components[1].status is ComponentStatus.DOWN


async def test_timeout_is_reported_as_down() -> None:
    started = time.perf_counter()
    report = await _service(StubProbe("slow", delay=0.2), timeout=0.01).check()
    elapsed = time.perf_counter() - started

    assert report.status is OverallStatus.UNAVAILABLE
    assert report.components[0].detail == "timed out after 0.01s"
    assert elapsed < 0.2


async def test_credentials_are_scrubbed_from_probe_errors() -> None:
    error = RuntimeError("could not connect to postgresql://admin:supersecret@db:5432/app")
    report = await _service(StubProbe("postgres", error=error)).check()

    detail = report.components[0].detail
    assert detail is not None
    assert "supersecret" not in detail
    assert "postgresql://***@db:5432/app" in detail


async def test_long_error_details_are_truncated() -> None:
    report = await _service(StubProbe("postgres", error=RuntimeError("x" * 1000))).check()

    detail = report.components[0].detail
    assert detail is not None
    assert len(detail) <= 300


def test_service_requires_probes() -> None:
    with pytest.raises(ValueError, match="at least one health probe"):
        HealthService(probes=(), version="1", environment="test")


def test_service_requires_positive_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        HealthService(probes=[StubProbe()], version="1", environment="test", timeout_seconds=0)


async def test_probes_run_concurrently() -> None:
    service = _service(
        StubProbe("a", delay=0.05),
        StubProbe("b", delay=0.05),
        StubProbe("c", delay=0.05),
    )

    started = time.perf_counter()
    await service.check()
    elapsed = time.perf_counter() - started

    # Sequential execution would take >= 0.15s; concurrency stays far below it.
    assert elapsed < 0.15


async def test_probe_implementations_delegate_to_infrastructure() -> None:
    database = StubPingable()
    qdrant = StubPingable()

    postgres_probe = PostgresProbe(database)
    qdrant_probe = QdrantProbe(qdrant)

    await postgres_probe.check()
    await qdrant_probe.check()

    assert postgres_probe.name == "postgres"
    assert qdrant_probe.name == "qdrant"
    assert postgres_probe.required is True
    assert qdrant_probe.required is True
    assert database.ping_count == 1
    assert qdrant.ping_count == 1


async def test_probe_failure_propagates_to_service() -> None:
    service = _service(StubProbe("postgres", error=RuntimeError("boom")))
    report = await service.check()

    assert report.components[0].status is ComponentStatus.DOWN
