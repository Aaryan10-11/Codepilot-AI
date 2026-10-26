"""Aggregates dependency probes into a single health report."""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Sequence
from datetime import UTC, datetime

from codepilot.models.health import (
    ComponentHealth,
    ComponentStatus,
    HealthReport,
    OverallStatus,
)
from codepilot.services.health.contracts import HealthProbe

_MAX_DETAIL_LENGTH = 300

# Mask user:password pairs inside URLs before they reach logs or API responses.
_URL_CREDENTIALS = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*://)[^/@\s]+@")


def _scrub(text: str) -> str:
    scrubbed = _URL_CREDENTIALS.sub(r"\g<scheme>***@", text)
    return scrubbed[:_MAX_DETAIL_LENGTH]


def _describe(exc: BaseException) -> str:
    message = str(exc).strip()
    if not message:
        return type(exc).__name__
    return _scrub(f"{type(exc).__name__}: {message}")


class HealthService:
    """Runs all probes concurrently and derives the aggregate status."""

    def __init__(
        self,
        *,
        probes: Sequence[HealthProbe],
        version: str,
        environment: str,
        timeout_seconds: float = 2.0,
        started_at: float | None = None,
    ) -> None:
        """Create the service.

        Args:
            probes: Dependency probes to execute on every check.
            version: Application version reported to operators.
            environment: Deployment environment name.
            timeout_seconds: Per-probe deadline; a slow dependency is unhealthy.
            started_at: ``time.monotonic()`` reference for uptime reporting.
        """
        if not probes:
            raise ValueError("at least one health probe is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._probes = tuple(probes)
        self._version = version
        self._environment = environment
        self._timeout_seconds = timeout_seconds
        self._started_at = time.monotonic() if started_at is None else started_at

    async def check(self) -> HealthReport:
        """Probe every dependency concurrently and return an aggregate report."""
        components = list(
            await asyncio.gather(*(self._check_one(probe) for probe in self._probes)),
        )
        return HealthReport(
            status=self._overall_status(components),
            version=self._version,
            environment=self._environment,
            checked_at=datetime.now(UTC),
            uptime_seconds=max(0.0, time.monotonic() - self._started_at),
            components=components,
        )

    async def _check_one(self, probe: HealthProbe) -> ComponentHealth:
        start = time.perf_counter()
        status = ComponentStatus.UP
        detail: str | None = None
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await probe.check()
        except TimeoutError:
            status = ComponentStatus.DOWN
            detail = f"timed out after {self._timeout_seconds:g}s"
        except Exception as exc:
            status = ComponentStatus.DOWN
            detail = _describe(exc)
        latency_ms = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name=probe.name,
            status=status,
            required=probe.required,
            latency_ms=round(latency_ms, 2),
            detail=detail,
        )

    @staticmethod
    def _overall_status(components: Sequence[ComponentHealth]) -> OverallStatus:
        if any(
            component.status is ComponentStatus.DOWN and component.required
            for component in components
        ):
            return OverallStatus.UNAVAILABLE
        if any(component.status is ComponentStatus.DOWN for component in components):
            return OverallStatus.DEGRADED
        return OverallStatus.OK
