"""Health-check domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ComponentStatus(StrEnum):
    """Observed state of a single dependency."""

    UP = "up"
    DOWN = "down"


class OverallStatus(StrEnum):
    """Aggregate health of the service."""

    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ComponentHealth(BaseModel):
    """Result of probing one dependency."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: ComponentStatus
    required: bool = True
    latency_ms: float = Field(ge=0)
    detail: str | None = None


class HealthReport(BaseModel):
    """Full health snapshot, safe to expose to operators."""

    status: OverallStatus
    version: str
    environment: str
    checked_at: datetime
    uptime_seconds: float = Field(ge=0)
    components: list[ComponentHealth]


class LivenessReport(BaseModel):
    """Minimal process-liveness response."""

    status: str = "ok"
    version: str
