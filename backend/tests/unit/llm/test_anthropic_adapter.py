"""Anthropic adapter tests against a real SSE-through-ASGI fake server."""

from __future__ import annotations

from typing import Any

import pytest
from httpx2 import ASGITransport
from httpx2 import AsyncClient as HttpxAsyncClient
from pydantic import SecretStr

from codepilot.llm.contracts import LLMProvider
from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderOverloadedError,
    ProviderRateLimitError,
    ProviderRequestError,
)
from codepilot.llm.providers.anthropic_adapter import AnthropicProvider
from codepilot.models.llm import (
    FinishReason,
    Message,
    MessageEndEvent,
    MessageRole,
    StreamEvent,
    TextDeltaEvent,
    TokenUsage,
    ToolCall,
    ToolCallDeltaEvent,
    ToolChoice,
    ToolSpec,
)
from tests.unit.llm.fakes import make_request
from tests.unit.llm.wire import FakeAnthropicApp, tool_use_events, tool_use_message


def build_provider(app: FakeAnthropicApp, **overrides: Any) -> AnthropicProvider:
    """Construct the adapter with a transport-backed SDK client."""
    return AnthropicProvider(
        api_key=SecretStr("sk-ant-test"),
        default_model=overrides.pop("default_model", "claude-prod"),
        base_url="http://testserver",
        http_client=HttpxAsyncClient(transport=ASGITransport(app=app), timeout=30.0),
        **overrides,
    )


async def test_adapter_satisfies_the_contract() -> None:
    assert isinstance(build_provider(FakeAnthropicApp()), LLMProvider)


async def test_complete_normalises_response() -> None:
    app = FakeAnthropicApp()
    provider = build_provider(app)

    result = await provider.complete(make_request(model="claude-mini"))

    assert result.content == "Hello there"
    assert result.finish_reason is FinishReason.STOP
    assert result.usage == TokenUsage(input_tokens=9, output_tokens=4, total_tokens=13)
    assert result.model == "claude-fake"

    sent = app.requests[0]
    assert sent["model"] == "claude-mini"
    assert sent["max_tokens"] == 8192
    assert "system" not in sent


async def test_complete_extracts_system_message() -> None:
    app = FakeAnthropicApp()
    provider = build_provider(app)
    request = make_request(
        messages=[
            Message(role=MessageRole.SYSTEM, content="Be terse."),
            Message(role=MessageRole.USER, content="hi"),
        ],
    )

    await provider.complete(request)

    sent = app.requests[0]
    assert sent["system"] == "Be terse."
    assert all(turn["role"] != "system" for turn in sent["messages"])


async def test_complete_translates_sampling_params() -> None:
    app = FakeAnthropicApp()
    provider = build_provider(app)

    await provider.complete(make_request(temperature=0.5, top_p=0.7, max_output_tokens=99))

    sent = app.requests[0]
    assert sent["temperature"] == 0.5
    assert sent["top_p"] == 0.7
    assert sent["max_tokens"] == 99


async def test_complete_translates_tool_calls_and_results() -> None:
    app = FakeAnthropicApp()
    app.message = tool_use_message()
    provider = build_provider(app)
    request = make_request(
        messages=[
            Message(role=MessageRole.USER, content="weather?"),
            Message(
                role=MessageRole.ASSISTANT,
                tool_calls=[
                    ToolCall(id="toolu_1", name="get_weather", arguments='{"city":"Paris"}'),
                ],
            ),
            Message(role=MessageRole.TOOL, tool_call_id="toolu_1", content="12C"),
        ],
    )

    result = await provider.complete(request)

    assert result.finish_reason is FinishReason.TOOL_CALLS
    assert result.tool_calls[0].name == "get_weather"
    sent = app.requests[0]
    turns = sent["messages"]
    assert turns[1]["content"][0]["type"] == "tool_use"
    assert turns[1]["content"][0]["input"] == {"city": "Paris"}
    assert turns[2]["role"] == "user"
    assert turns[2]["content"] == [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_1",
            "content": [{"type": "text", "text": "12C"}],
        },
    ]


async def test_complete_merges_consecutive_tool_results() -> None:
    app = FakeAnthropicApp()
    provider = build_provider(app)
    tools = [
        ToolCall(id="toolu_1", name="first", arguments="{}"),
        ToolCall(id="toolu_2", name="second", arguments="{}"),
    ]
    request = make_request(
        messages=[
            Message(
                role=MessageRole.ASSISTANT,
                tool_calls=[tools[0], tools[1]],
            ),
            Message(role=MessageRole.TOOL, tool_call_id="toolu_1", content="a"),
            Message(role=MessageRole.TOOL, tool_call_id="toolu_2", content="b"),
            Message(role=MessageRole.USER, content="been busy"),
        ],
    )

    await provider.complete(request)

    turns = app.requests[0]["messages"]
    assert len(turns) == 2
    assert turns[1]["role"] == "user"
    assert len(turns[1]["content"]) == 3


async def test_complete_rejects_tools_with_none_choice() -> None:
    app = FakeAnthropicApp()
    provider = build_provider(app)
    request = make_request(
        tools=[ToolSpec(name="do", description="d", parameters={"type": "object"})],
        tool_choice=ToolChoice.NONE,
    )

    await provider.complete(request)
    sent = app.requests[0]
    assert "tools" not in sent
    assert "tool_choice" not in sent


async def test_stream_emits_normalized_events() -> None:
    app = FakeAnthropicApp()
    provider = build_provider(app)

    events: list[StreamEvent] = [event async for event in provider.stream(make_request())]

    types = [event.type for event in events]
    assert types == ["message_start", "text_delta", "text_delta", "message_end"]
    deltas = [event.text for event in events if isinstance(event, TextDeltaEvent)]
    assert deltas == ["Hello", " there"]
    end = events[-1]
    assert isinstance(end, MessageEndEvent)
    assert end.finish_reason is FinishReason.STOP
    assert end.usage == TokenUsage(input_tokens=9, output_tokens=4, total_tokens=None)


async def test_stream_conveys_tool_call_deltas() -> None:
    app = FakeAnthropicApp()
    app.events = tool_use_events()
    provider = build_provider(app)

    events: list[StreamEvent] = [event async for event in provider.stream(make_request())]

    tool_events = [event for event in events if isinstance(event, ToolCallDeltaEvent)]
    assert tool_events[0].id == "toolu_9"
    assert tool_events[0].name == "get_weather"
    joined = "".join(event.arguments_delta for event in tool_events)
    assert joined == '{"city":"Paris"}'
    end = events[-1]
    assert isinstance(end, MessageEndEvent)
    assert end.finish_reason is FinishReason.TOOL_CALLS


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, ProviderAuthError),
        (429, ProviderRateLimitError),
        (529, ProviderOverloadedError),
        (400, ProviderRequestError),
    ],
)
async def test_error_mapping(status: int, expected: type[Exception]) -> None:
    app = FakeAnthropicApp(status=status)
    provider = build_provider(app)

    with pytest.raises(expected):
        await provider.complete(make_request())


async def test_rate_limit_error_carries_retry_after() -> None:
    app = FakeAnthropicApp(status=429)
    provider = build_provider(app)

    with pytest.raises(ProviderRateLimitError) as excinfo:
        await provider.complete(make_request())

    assert excinfo.value.retry_after == 7.0
