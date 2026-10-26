"""Health-check contracts and probes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Pingable(Protocol):
    """Minimal capability required by a connectivity probe."""

    async def ping(self) -> None:
        """Raise if the dependency is unreachable; return ``None`` when healthy."""
        ...


@runtime_checkable
class HealthProbe(Protocol):
    """A named readiness check for one dependency."""

    @property
    def name(self) -> str:
        """Stable component name reported to operators."""
        ...

    @property
    def required(self) -> bool:
        """Whether a failure makes the whole service unavailable."""
        ...

    async def check(self) -> None:
        """Raise if the component is unhealthy; return ``None`` when healthy."""
        ...
