"""OpenAI adapter tests against a real SSE-through-ASGI fake server."""

from __future__ import annotations

from typing import Any

import pytest
from httpx2 import ASGITransport
from httpx2 import AsyncClient as HttpxAsyncClient

from codepilot.llm.contracts import LLMProvider
from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderOverloadedError,
    ProviderRateLimitError,
    ProviderRequestError,
)
from codepilot.llm.providers.openai_adapter import OpenAICompatibleProvider
from codepilot.models.llm import (
    FinishReason,
    MessageEndEvent,
    StreamEvent,
    TokenUsage,
    ToolCallDeltaEvent,
)
from tests.unit.llm.fakes import make_request
from tests.unit.llm.wire import FakeOpenAIApp, tool_call_chunks, tool_call_completion


def build_provider(app: FakeOpenAIApp, **overrides: Any) -> OpenAICompatibleProvider:
    """Construct the adapter with a transport-backed SDK client."""
    http_client = HttpxAsyncClient(
        transport=ASGITransport(app=app),
        timeout=30.0,
    )
    return OpenAICompatibleProvider(
        api_key="sk-test",
        default_model=overrides.pop("default_model", "gpt-fake-prod"),
        base_url="http://testserver/v1/",
        http_client=http_client,
        **overrides,
    )


async def test_adapter_satisfies_the_contract() -> None:
    app = FakeOpenAIApp()
    provider = build_provider(app)
    assert isinstance(provider, LLMProvider)


async def test_complete_normalises_response() -> None:
    app = FakeOpenAIApp()
    provider = build_provider(app)

    result = await provider.complete(make_request(model="gpt-mini"))

    assert result.content == "Hello there"
    assert result.tool_calls == []
    assert result.finish_reason is FinishReason.STOP
    assert result.usage == TokenUsage(input_tokens=4, output_tokens=3, total_tokens=7)
    assert result.model == "gpt-fake"

    sent = app.requests[0]
    assert sent["model"] == "gpt-mini"
    assert sent["messages"] == [{"role": "user", "content": "hello"}]
    assert "temperature" not in sent


async def test_complete_translates_sampling_params_and_tools() -> None:
    app = FakeOpenAIApp()
    provider = build_provider(app)
    request = make_request(
        temperature=0.3,
        top_p=0.9,
        max_output_tokens=256,
        stop_sequences=["END"],
    )

    await provider.complete(request)

    sent = app.requests[0]
    assert sent["temperature"] == 0.3
    assert sent["top_p"] == 0.9
    assert sent["max_tokens"] == 256
    assert sent["stop"] == ["END"]


async def test_complete_maps_tool_calls() -> None:
    app = FakeOpenAIApp()
    app.completion = tool_call_completion()
    provider = build_provider(app)

    result = await provider.complete(make_request())

    assert result.content is None
    assert result.finish_reason is FinishReason.TOOL_CALLS
    call = result.tool_calls[0]
    assert call.id == "call_9"
    assert call.name == "get_weather"
    assert call.arguments == '{"city":"Paris"}'


async def test_stream_emits_normalized_events() -> None:
    app = FakeOpenAIApp()
    provider = build_provider(app)

    events: list[StreamEvent] = [event async for event in provider.stream(make_request())]

    types = [event.type for event in events]
    assert types == ["message_start", "text_delta", "text_delta", "message_end"]
    deltas = [event.text for event in events if event.type == "text_delta"]
    assert deltas == ["Hello", " there"]
    end = events[-1]
    assert isinstance(end, MessageEndEvent)
    assert end.finish_reason is FinishReason.STOP
    assert end.usage == TokenUsage(input_tokens=4, output_tokens=3, total_tokens=7)
    assert end.model == "gpt-fake"

    sent = app.requests[0]
    assert "stream_options" in sent


async def test_stream_conveys_tool_call_deltas() -> None:
    app = FakeOpenAIApp()
    app.chunks = tool_call_chunks()
    provider = build_provider(app)

    events: list[StreamEvent] = [event async for event in provider.stream(make_request())]

    tool_events = [event for event in events if isinstance(event, ToolCallDeltaEvent)]
    assert tool_events[0].id == "call_1"
    assert tool_events[0].name == "get_weather"
    assert "".join(event.arguments_delta or "" for event in tool_events) == '{"city":"Paris"}'
    end = events[-1]
    assert isinstance(end, MessageEndEvent)
    assert end.finish_reason is FinishReason.TOOL_CALLS


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, ProviderAuthError),
        (429, ProviderRateLimitError),
        (500, ProviderOverloadedError),
        (400, ProviderRequestError),
    ],
)
async def test_error_mapping(status: int, expected: type[Exception]) -> None:
    app = FakeOpenAIApp(status=status)
    provider = build_provider(app)

    with pytest.raises(expected):
        await provider.complete(make_request())


async def test_rate_limit_error_carries_retry_after() -> None:
    app = FakeOpenAIApp(status=429)
    provider = build_provider(app)

    with pytest.raises(ProviderRateLimitError) as excinfo:
        await provider.complete(make_request())

    assert excinfo.value.retry_after == 3.0
    assert excinfo.value.http_status == 503


async def test_properties_report_configuration() -> None:
    provider = build_provider(FakeOpenAIApp(), default_model="custom-model")

    assert provider.provider_id.value == "openai"
    assert provider.default_model == "custom-model"
    assert provider.capabilities.tool_calling is True
