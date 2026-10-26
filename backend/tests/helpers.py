"""Test doubles shared across suites."""

from __future__ import annotations

import asyncio


class StubProbe:
    """Configurable health probe implementing the ``HealthProbe`` protocol."""

    def __init__(
        self,
        name: str = "stub",
        *,
        required: bool = True,
        error: BaseException | None = None,
        delay: float = 0.0,
    ) -> None:
        self._name = name
        self._required = required
        self._error = error
        self._delay = delay

    @property
    def name(self) -> str:
        return self._name

    @property
    def required(self) -> bool:
        return self._required

    async def check(self) -> None:
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error


class StubPingable:
    """Records ping calls and optionally fails."""

    def __init__(self, error: BaseException | None = None) -> None:
        self._error = error
        self.ping_count = 0

    async def ping(self) -> None:
        self.ping_count += 1
        if self._error is not None:
            raise self._error
