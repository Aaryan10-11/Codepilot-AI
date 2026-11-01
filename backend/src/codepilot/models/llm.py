"""Provider-neutral LLM domain models.

Pure from the project's perspective: only ``pydantic`` is imported here. The
adapters in ``codepilot.llm.providers`` translate between these models and each
vendor's wire format; vendor types never leak beyond that boundary.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderId(StrEnum):
    """Identifiers for the first-party supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"


class MessageRole(StrEnum):
    """Roles supported across every provider."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(StrEnum):
    """Why a completion ended, normalised across providers."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    OTHER = "other"


class ToolChoice(StrEnum):
    """How aggressively the model should call tools."""

    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"


class ToolSpec(BaseModel):
    """A tool the model may call.

    Attributes:
        name: Unique identifier the model uses to reference the tool.
        description: Natural-language explanation consumed by the model.
        parameters: JSON Schema object describing the tool arguments.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """A tool invocation requested by the model.

    ``arguments`` keeps the provider's original JSON text so that streaming
    partials can be stitched back together losslessly.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: str = "{}"


class Message(BaseModel):
    """One conversation turn, normalised across providers."""

    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> Message:
        """Reject shapes no provider can represent."""
        if self.role is MessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool messages require tool_call_id")
        if self.content is None and not self.tool_calls:
            raise ValueError("message requires content or tool_calls")
        if self.content is not None and not self.content.strip() and not self.tool_calls:
            raise ValueError("message content must not be blank")
        return self


class TokenUsage(BaseModel):
    """Token accounting for one completion or the sum of many."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Sum two usage records; ``None`` totals are carried or derived."""
        total = None
        if self.total_tokens is not None or other.total_tokens is not None:
            total = _or_zero(self.total_tokens) + _or_zero(other.total_tokens)
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=total,
        )


def _or_zero(value: int | None) -> int:
    return value if value is not None else 0


class CompletionRequest(BaseModel):
    """Everything a provider needs to produce one completion."""

    messages: list[Message] = Field(min_length=1)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_output_tokens: int | None = Field(default=None, gt=0)
    tools: list[ToolSpec] = Field(default_factory=list)
    tool_choice: ToolChoice | None = None
    stop_sequences: list[str] = Field(default_factory=list)


class CompletionResult(BaseModel):
    """The normalised outcome of one completion."""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: FinishReason = FinishReason.OTHER
    usage: TokenUsage | None = None
    model: str | None = None


class MessageStartEvent(BaseModel):
    """Emitted once, before any content, at the beginning of a stream."""

    type: Literal["message_start"] = "message_start"


class TextDeltaEvent(BaseModel):
    """An increment of assistant text."""

    type: Literal["text_delta"] = "text_delta"
    text: str = Field(min_length=1)


class ToolCallDeltaEvent(BaseModel):
    """An increment of a tool call.

    ``index`` positions the call within the response; identifiers and names
    arrive on the first delta for that index and may be ``None`` afterwards.
    """

    type: Literal["tool_call_delta"] = "tool_call_delta"
    index: int = Field(ge=0)
    id: str | None = None
    name: str | None = None
    arguments_delta: str = ""


class MessageEndEvent(BaseModel):
    """The final event of every stream; carries the authoritative usage."""

    type: Literal["message_end"] = "message_end"
    finish_reason: FinishReason = FinishReason.OTHER
    usage: TokenUsage | None = None
    model: str | None = None


StreamEvent = Annotated[
    MessageStartEvent | TextDeltaEvent | ToolCallDeltaEvent | MessageEndEvent,
    Field(discriminator="type"),
]


class ProviderCapabilities(BaseModel):
    """What a provider/model pair can do; adapters report honest values."""

    model_config = ConfigDict(frozen=True)

    streaming: bool = True
    tool_calling: bool = True
    json_mode: bool = True
    vision: bool = False
    context_window_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)


class ProviderRecord(BaseModel):
    """A provider as reported to clients, without secrets."""

    model_config = ConfigDict(frozen=True)

    id: ProviderId
    configured: bool
    default_model: str
