"""Domain model invariants for the LLM layer."""

from __future__ import annotations

import pytest

from codepilot.models.llm import (
    FinishReason,
    Message,
    MessageEndEvent,
    MessageRole,
    TokenUsage,
    ToolCall,
    ToolChoice,
    ToolSpec,
)


def test_token_usage_adds_records() -> None:
    total = TokenUsage(input_tokens=5, output_tokens=7, total_tokens=12)
    other = TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)

    merged = total + other

    assert merged.input_tokens == 6
    assert merged.output_tokens == 9
    assert merged.total_tokens == 15


def test_token_usage_tolerates_missing_totals() -> None:
    first = TokenUsage(input_tokens=5, output_tokens=7)
    second = TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)

    merged = first + second

    assert merged.total_tokens == 3
    assert (second + first).total_tokens == 3


def test_tool_messages_require_tool_call_id() -> None:
    with pytest.raises(ValueError):
        Message(role=MessageRole.TOOL, content="result")


def test_messages_require_content_or_tool_calls() -> None:
    with pytest.raises(ValueError):
        Message(role=MessageRole.ASSISTANT)
    with pytest.raises(ValueError):
        Message(role=MessageRole.ASSISTANT, content="   ")


def test_message_with_only_tool_calls_is_valid() -> None:
    message = Message(
        role=MessageRole.ASSISTANT,
        tool_calls=[ToolCall(id="call_1", name="noop")],
    )
    assert message.role is MessageRole.ASSISTANT


def test_tool_spec_helps_pydantic_imports_stay_in_use() -> None:
    spec = ToolSpec(name="noop", description="does nothing", parameters={"type": "object"})
    assert spec.name == "noop"


def test_finish_reasons_and_choices_are_enumerable() -> None:
    assert FinishReason.OTHER.value == "other"
    assert ToolChoice.REQUIRED.value == "required"


def test_message_end_default_carries_other_reason() -> None:
    event = MessageEndEvent()
    assert event.finish_reason is FinishReason.OTHER
