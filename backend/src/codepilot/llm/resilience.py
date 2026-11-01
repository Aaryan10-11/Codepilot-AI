"""Retry behavior for provider calls.

The resilience wrapper sits between agents and adapters: it retries failures
marked ``retryable`` in ``codepilot.llm.errors`` and never touches anything
else. Timing is injected so tests are deterministic.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

import structlog

from codepilot.config.settings import RetrySettings
from codepilot.llm.contracts import LLMProvider
from codepilot.llm.errors import ProviderError
from codepilot.models.llm import (
    CompletionRequest,
    CompletionResult,
    ProviderCapabilities,
    ProviderId,
    StreamEvent,
)

logger = structlog.get_logger(__name__)

SleepFn = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class RetryPolicy:
    """Delay schedule for transient provider failures."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    jitter: float = 0.1
    sleep: SleepFn = field(default=asyncio.sleep)

    def __post_init__(self) -> None:
        """Reject schedules that cannot make progress."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.jitter < 0:
            raise ValueError("jitter must not be negative")

    @classmethod
    def from_settings(cls, settings: RetrySettings) -> RetryPolicy:
        """Build the default policy from configuration."""
        return cls(
            max_attempts=settings.max_attempts,
            base_delay_seconds=settings.base_delay_seconds,
            max_delay_seconds=settings.max_delay_seconds,
            jitter=settings.jitter,
        )

    def delay(self, attempt: int, *, retry_after: float | None = None) -> float:
        """Compute the wait before ``attempt``+1.

        A server-provided ``retry_after`` is honoured, clamped to one minute;
        otherwise the schedule is exponential backoff with uniform jitter.
        """
        if retry_after is not None and retry_after > 0:
            return min(retry_after, 60.0)
        exponent = min(attempt - 1, 4)
        delay: float = self.base_delay_seconds * (2**exponent)
        capped: float = min(delay, self.max_delay_seconds)
        factor: float = 1 + random.uniform(0, self.jitter)  # noqa: S311 - jitter, not crypto
        return capped * factor


class RetryingProvider:
    """Decorates any ``LLMProvider`` with transient-failure retries.

    ``complete`` is retried fully; ``stream`` is retried only while no event
    has been forwarded, because once content reaches a consumer it must not be
    replayed. Non-retryable failures and exhausted budgets propagate.
    """

    def __init__(self, wrapped: LLMProvider, policy: RetryPolicy) -> None:
        """Bind the policy to a provider instance."""
        self._wrapped = wrapped
        self._policy = policy

    @classmethod
    def from_settings(
        cls,
        policy: RetrySettings,
        wrapped: LLMProvider,
    ) -> RetryingProvider:
        """Wrap ``wrapped`` with the retry policy resolved from settings."""
        return cls(wrapped, RetryPolicy.from_settings(policy))

    @property
    def provider_id(self) -> ProviderId:
        """The wrapped provider's identifier."""
        return self._wrapped.provider_id

    @property
    def default_model(self) -> str:
        """The wrapped provider's default model."""
        return self._wrapped.default_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        """The wrapped provider's capabilities."""
        return self._wrapped.capabilities

    @property
    def wrapped(self) -> LLMProvider:
        """The underlying provider, for tests and diagnostics."""
        return self._wrapped

    async def verify(self) -> None:
        """Forward the credential check without retries."""
        await self._wrapped.verify()

    async def close(self) -> None:
        """Forward shutdown to the wrapped provider."""
        await self._wrapped.close()

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Run one completion, retrying transient provider failures."""
        last_error: ProviderError | None = None
        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                return await self._wrapped.complete(request)
            except ProviderError as error:
                if not error.retryable:
                    raise
                last_error = error
                if attempt == self._policy.max_attempts:
                    break
                delay = self._policy.delay(attempt, retry_after=error.retry_after)
                logger.warning(
                    "llm_retry_scheduled",
                    provider=self.provider_id.value,
                    error_code=error.code,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    delay_seconds=round(delay, 3),
                )
                await self._policy.sleep(delay)
        assert last_error is not None  # noqa: S101 - loop always sets or raises
        raise last_error

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Forward provider events; re-open the stream only before the first one."""
        attempt = 0
        while True:
            attempt += 1
            iterator = self._wrapped.stream(request)
            try:
                first = await anext(iterator)
            except StopAsyncIteration:
                return
            except ProviderError as error:
                if error.retryable and attempt < self._policy.max_attempts:
                    delay = self._policy.delay(attempt, retry_after=error.retry_after)
                    logger.warning(
                        "llm_stream_retry_scheduled",
                        provider=self.provider_id.value,
                        error_code=error.code,
                        attempt=attempt,
                        delay_seconds=round(delay, 3),
                    )
                    await self._policy.sleep(delay)
                    continue
                raise
            yield first
            async for event in iterator:
                yield event
            return
