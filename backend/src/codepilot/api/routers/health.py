"""Liveness and readiness endpoints."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Response

from codepilot import __version__
from codepilot.api.deps import HealthServiceDep
from codepilot.models.health import HealthReport, LivenessReport, OverallStatus

router = APIRouter(prefix="/v1", tags=["health"])


@router.get(
    "/health/live",
    response_model=LivenessReport,
    summary="Process liveness",
    description="Returns 200 whenever the process can serve requests. No dependency is probed.",
)
async def liveness() -> LivenessReport:
    """Confirm that the process is running."""
    return LivenessReport(version=__version__)


@router.get(
    "/health/ready",
    response_model=HealthReport,
    summary="Dependency readiness",
    description=(
        "Probes every required dependency. Returns 503 when any required "
        "component is down, 200 otherwise."
    ),
    responses={
        HTTPStatus.SERVICE_UNAVAILABLE: {
            "model": HealthReport,
            "description": "At least one required dependency is unavailable.",
        },
    },
)
async def readiness(service: HealthServiceDep, response: Response) -> HealthReport:
    """Report readiness, using HTTP status for load balancers."""
    report = await service.check()
    if report.status is OverallStatus.UNAVAILABLE:
        response.status_code = HTTPStatus.SERVICE_UNAVAILABLE
    return report


@router.get(
    "/health",
    response_model=HealthReport,
    summary="Full health snapshot",
    description=(
        "Returns the status of every dependency. Always responds 200 so that "
        "dashboards can render partial failures."
    ),
)
async def health(service: HealthServiceDep) -> HealthReport:
    """Return the full component-level health report."""
    return await service.check()
