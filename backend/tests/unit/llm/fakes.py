"""In-memory provider doubles implementing the ``LLMProvider`` contract."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from codepilot.models.llm import (
    CompletionRequest,
    CompletionResult,
    FinishReason,
    Message,
    MessageEndEvent,
    MessageRole,
    MessageStartEvent,
    ProviderCapabilities,
    ProviderId,
    StreamEvent,
    TextDeltaEvent,
    TokenUsage,
)


def make_request(**overrides: object) -> CompletionRequest:
    """Build a minimal valid completion request."""
    payload: dict[str, object] = {
        "messages": [Message(role=MessageRole.USER, content="hello")],
    }
    payload.update(overrides)
    return CompletionRequest(**payload)


class ScriptedProvider:
    """Returns queued results/events; records every call it receives."""

    def __init__(
        self,
        *,
        provider_id: ProviderId = ProviderId.OPENAI,
        results: list[CompletionResult | Exception] | None = None,
        streams: list[list[object]] | None = None,
        stream_errors: list[Exception] | None = None,
        verify_error: Exception | None = None,
    ) -> None:
        """Script the behavior for each queued ``complete``/``stream`` call."""
        self.provider_id_value = provider_id
        self._verify_error = verify_error
        self._capabilities = ProviderCapabilities()
        self._results = list(results or [])
        self._result_index = 0
        self._streams = list(streams or [])
        self._stream_index = 0
        self._stream_errors = list(stream_errors or [])
        self.complete_requests: list[CompletionRequest] = []
        self.stream_requests: list[CompletionRequest] = []
        self.verify_calls = 0
        self.close_calls = 0

    @property
    def provider_id(self) -> ProviderId:
        """Configured identifier for this fake."""
        return self.provider_id_value

    @property
    def default_model(self) -> str:
        """Stable fake model name."""
        return "fake-model"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Full capabilities; tests override behavior, not capabilities."""
        return self._capabilities

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Return the next scripted result or raise it."""
        self.complete_requests.append(request)
        item = self._results[min(self._result_index, len(self._results) - 1)]
        self._result_index += 1
        if isinstance(item, Exception):
            raise item
        return item

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Play the next scripted stream; raises queued errors before starting.

        ``stream_errors`` are consumed one per ``stream`` call and raised before
        any event, simulating a failure while opening the stream. Scripts may
        also embed ``Exception`` instances, which are raised at that point
        mid-stream.
        """
        self.stream_requests.append(request)
        if self._stream_errors:
            error = self._stream_errors.pop(0)
            if error is not None:
                raise error
        events = self._streams[min(self._stream_index, len(self._streams) - 1)]
        self._stream_index += 1
        for item in events:
            if isinstance(item, Exception):
                raise item
            yield cast(StreamEvent, item)

    async def verify(self) -> None:
        """Record the call; raises the scripted error when present."""
        self.verify_calls += 1
        if self._verify_error is not None:
            raise self._verify_error

    async def close(self) -> None:
        """Record the call."""
        self.close_calls += 1


def text_result(content: str = "answer") -> CompletionResult:
    """A simple text completion result with usage."""
    return CompletionResult(
        content=content,
        finish_reason=FinishReason.STOP,
        usage=TokenUsage(input_tokens=3, output_tokens=5, total_tokens=8),
        model="fake-model",
    )


def text_stream(text: str = "answer") -> list[object]:
    """A canonical three-event text stream."""
    return [
        MessageStartEvent(),
        TextDeltaEvent(text=text),
        MessageEndEvent(
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(input_tokens=3, output_tokens=5, total_tokens=8),
            model="fake-model",
        ),
    ]
