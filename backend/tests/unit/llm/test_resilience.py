"""Retry policy and retrying-provider tests against scripted doubles."""

from __future__ import annotations

import pytest

from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderOverloadedError,
    ProviderRateLimitError,
)
from codepilot.llm.resilience import RetryingProvider, RetryPolicy
from codepilot.models.llm import FinishReason, MessageEndEvent, StreamEvent
from tests.unit.llm.fakes import ScriptedProvider, make_request, text_result, text_stream


class SleepRecorder:
    """Collects scheduled delays instead of actually waiting."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)
        return None


def wrapping(provider: ScriptedProvider, **policy: object) -> RetryingProvider:
    sleep = policy.pop("sleep", None) or SleepRecorder()
    return RetryingProvider(provider, RetryPolicy(sleep=sleep, **policy))  # type: ignore[arg-type]


async def test_retry_policy_honours_retry_after() -> None:
    policy = RetryPolicy()
    assert policy.delay(1, retry_after=10.5) == 10.5
    assert policy.delay(1, retry_after=120) == 60.0
    assert policy.delay(1, retry_after=0) >= 0.5


async def test_retry_schedule_is_exponential_and_capped() -> None:
    policy = RetryPolicy(base_delay_seconds=0.5, max_delay_seconds=4.0, jitter=0.0)
    assert policy.delay(1) == pytest.approx(0.5)
    assert policy.delay(2) == pytest.approx(1.0)
    assert policy.delay(3) == pytest.approx(2.0)
    assert policy.delay(9) == pytest.approx(4.0)


async def test_complete_retries_transient_failures() -> None:
    transient = ProviderOverloadedError("overloaded", provider="openai")
    provider = ScriptedProvider(results=[transient, text_result()])
    wrapped = wrapping(provider, max_attempts=3)

    result = await wrapped.complete(make_request())

    assert result.content == "answer"
    assert len(provider.complete_requests) == 2


async def test_complete_does_not_retry_auth_failures() -> None:
    provider = ScriptedProvider(
        results=[ProviderAuthError("bad key", provider="openai")],
    )
    wrapped = wrapping(provider, max_attempts=3)

    with pytest.raises(ProviderAuthError):
        await wrapped.complete(make_request())

    assert len(provider.complete_requests) == 1


async def test_complete_raises_after_exhausted_attempts() -> None:
    provider = ScriptedProvider(results=[ProviderOverloadedError("down", provider="openai")])
    wrapped = wrapping(provider, max_attempts=2, base_delay_seconds=0.01)

    with pytest.raises(ProviderOverloadedError):
        await wrapped.complete(make_request())

    assert len(provider.complete_requests) == 2


async def test_retries_observe_rate_limit_delay() -> None:
    recorder = SleepRecorder()
    provider = ScriptedProvider(
        results=[
            ProviderRateLimitError("slow down", provider="openai", retry_after=2.5),
            text_result(),
        ],
    )
    wrapped = wrapping(provider, sleep=recorder, max_attempts=2)

    await wrapped.complete(make_request())

    assert recorder.delays == [pytest.approx(2.5)]


async def test_stream_retries_before_first_event() -> None:
    transient = ProviderOverloadedError("blip", provider="openai")
    provider = ScriptedProvider(
        stream_errors=[transient],
        streams=[[*text_stream("retry-ok")]],
    )
    wrapped = wrapping(provider, max_attempts=3, base_delay_seconds=0.01)

    events: list[StreamEvent] = []
    async for event in wrapped.stream(make_request()):
        events.append(event)

    assert [event.type for event in events] == [
        "message_start",
        "text_delta",
        "message_end",
    ]
    end = events[-1]
    assert isinstance(end, MessageEndEvent)
    assert end.finish_reason is FinishReason.STOP


async def test_stream_does_not_retry_after_first_event() -> None:
    mid_stream = ProviderOverloadedError("mid-stream", provider="openai")
    provider = ScriptedProvider(
        streams=[[*text_stream(), mid_stream]],
    )
    wrapped = wrapping(provider, max_attempts=3)

    collected: list[StreamEvent] = []
    with pytest.raises(ProviderOverloadedError):
        async for event in wrapped.stream(make_request()):
            collected.append(event)

    assert len(provider.stream_requests) == 1


async def test_delegation_passes_through_properties_and_lifecycle() -> None:
    provider = ScriptedProvider()
    wrapped = wrapping(provider)

    assert wrapped.provider_id is provider.provider_id
    assert wrapped.default_model == provider.default_model
    assert wrapped.capabilities is provider.capabilities

    await wrapped.verify()
    await wrapped.close()

    assert provider.verify_calls == 1
    assert provider.close_calls == 1


async def test_retry_policy_rejects_zero_attempts() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
