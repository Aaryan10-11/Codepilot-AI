"""Anthropic Messages adapter.

All ``anthropic`` SDK types stay inside this module. Wire details handled
here: the ``system`` parameter is assembled from system-role messages,
``max_tokens`` is mandatory, and tool results travel inside user turns.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    BadRequestError,
    OverloadedError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from anthropic import (
    NotFoundError as AnthropicNotFoundError,
)
from anthropic.types import (
    InputJSONDelta,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextDelta,
)
from pydantic import SecretStr

from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderOverloadedError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
)
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
    ToolCall,
    ToolCallDeltaEvent,
    ToolChoice,
)

logger = structlog.get_logger(__name__)

_FINISH_REASONS: dict[str | None, FinishReason] = {
    "end_turn": FinishReason.STOP,
    "stop_sequence": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "tool_use": FinishReason.TOOL_CALLS,
    "refusal": FinishReason.CONTENT_FILTER,
}

_DEFAULT_MAX_OUTPUT_TOKENS = 8192


class AnthropicProvider:
    """Adapter for the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: SecretStr | str,
        default_model: str,
        base_url: str | None = None,
        timeout_seconds: float = 180.0,
        capabilities: ProviderCapabilities | None = None,
        http_client: Any = None,
    ) -> None:
        """Build the adapter around one ``AsyncAnthropic`` client.

        SDK retries are disabled; the resilience layer owns that policy.

        Args:
            api_key: Secret already resolved from settings/environment.
            default_model: Model used when a request does not name one.
            base_url: Optional endpoint override.
            timeout_seconds: Per-call HTTP deadline.
            capabilities: Override for the advertised capability set.
            http_client: SDK-format async HTTP client; tests inject one.
        """
        self._default_model = default_model
        self._capabilities = capabilities or ProviderCapabilities()
        client_kwargs: dict[str, Any] = {
            "api_key": api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key,
            "timeout": timeout_seconds,
            "max_retries": 0,
        }
        if base_url is not None:
            client_kwargs["base_url"] = base_url
        if http_client is not None:
            client_kwargs["http_client"] = http_client
        self._client = AsyncAnthropic(**client_kwargs)

    @property
    def provider_id(self) -> ProviderId:
        """Anthropic's stable identifier."""
        return ProviderId.ANTHROPIC

    @property
    def default_model(self) -> str:
        """Model used when a request does not name one."""
        return self._default_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Advertised capabilities for this endpoint."""
        return self._capabilities

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Run one non-streaming completion."""
        params = self._base_params(request)
        try:
            response = await self._client.messages.create(**params)
        except APIStatusError as error:
            raise _map_status_error(error) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error

        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=json.dumps(block.input) if block.input else "{}",
                    ),
                )
            elif block.type == "text":
                content_parts.append(block.text)
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens or 0,
            output_tokens=response.usage.output_tokens or 0,
            total_tokens=(response.usage.input_tokens or 0) + (response.usage.output_tokens or 0),
        )
        return CompletionResult(
            content="\n".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
            finish_reason=_FINISH_REASONS.get(response.stop_reason, FinishReason.OTHER),
            usage=usage,
            model=response.model,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Stream normalized events ending with ``message_end``."""
        params = self._base_params(request)
        params["stream"] = True
        try:
            event_stream = await self._client.messages.create(**params)
        except APIStatusError as error:
            raise _map_status_error(error) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error

        yield MessageStartEvent()
        input_tokens = 0
        output_tokens = 0
        finish_reason: FinishReason | None = None
        model: str | None = None
        try:
            async for event in event_stream:
                if isinstance(event, RawMessageStartEvent):
                    input_tokens = event.message.usage.input_tokens or 0
                    model = event.message.model
                    continue
                if isinstance(event, RawContentBlockStartEvent):
                    block = event.content_block
                    if block.type == "tool_use":
                        yield ToolCallDeltaEvent(
                            index=event.index,
                            id=block.id,
                            name=block.name,
                            arguments_delta="",
                        )
                    continue
                if isinstance(event, RawContentBlockDeltaEvent):
                    delta = event.delta
                    if isinstance(delta, TextDelta):
                        yield TextDeltaEvent(text=delta.text)
                    elif isinstance(delta, InputJSONDelta):
                        yield ToolCallDeltaEvent(
                            index=event.index,
                            id=None,
                            name=None,
                            arguments_delta=delta.partial_json,
                        )
                    continue
                if isinstance(event, RawMessageDeltaEvent):
                    finish_reason = _FINISH_REASONS.get(event.delta.stop_reason, FinishReason.OTHER)
                    output_tokens = event.usage.output_tokens or 0
                    continue
                if isinstance(event, RawMessageStopEvent):
                    continue
        except APIStatusError as error:
            raise _map_status_error(error) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error
        yield MessageEndEvent(
            finish_reason=finish_reason or FinishReason.OTHER,
            usage=TokenUsage(
                input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=None
            ),
            model=model or self._default_model,
        )

    async def verify(self) -> None:
        """Confirm credentials with one cheap authenticated request."""
        try:
            page = await self._client.models.list(limit=1)
            _ = page.data
        except APIStatusError as error:
            raise _map_status_error(error) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.close()

    def _timeout_error(self) -> ProviderTimeoutError:
        """Build the typed timeout error for this provider."""
        return ProviderTimeoutError("provider timed out", provider=self.provider_id.value)

    def _connection_error(self) -> ProviderConnectionError:
        """Build the typed connection error for this provider."""
        return ProviderConnectionError("could not reach provider", provider=self.provider_id.value)

    def _base_params(self, request: CompletionRequest) -> dict[str, Any]:
        """Translate a domain request into Messages API parameters."""
        system_text, turns = _split_messages(request.messages)
        params: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": turns,
            "max_tokens": request.max_output_tokens or _DEFAULT_MAX_OUTPUT_TOKENS,
        }
        if system_text:
            params["system"] = system_text
        # The Anthropic SDK (v2) no longer types sampling knobs on ``create``;
        # they are still accepted as top-level body fields, passed via extra_body.
        extra_body: dict[str, Any] = {}
        if request.temperature is not None:
            extra_body["temperature"] = request.temperature
        if request.top_p is not None:
            extra_body["top_p"] = request.top_p
        if extra_body:
            params["extra_body"] = extra_body
        if request.stop_sequences:
            params["stop_sequences"] = request.stop_sequences
        tools_enabled = bool(request.tools) and request.tool_choice is not ToolChoice.NONE
        if tools_enabled:
            params["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in request.tools
            ]
            params["tool_choice"] = (
                {"type": "any"} if request.tool_choice is ToolChoice.REQUIRED else {"type": "auto"}
            )
        return params


def _split_messages(messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
    """Extract system text and build alternating, provider-shaped turns.

    System-role messages are joined into the ``system`` parameter. Tool-role
    and user messages merge into single user turns so the wire format always
    alternates user/assistant.
    """
    system_parts: list[str] = []
    turns: list[dict[str, Any]] = []

    def _append_turn(role: str, blocks: list[dict[str, Any]]) -> None:
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"].extend(blocks)
        else:
            turns.append({"role": role, "content": blocks})

    for message in messages:
        if message.role is MessageRole.SYSTEM:
            if message.content:
                system_parts.append(message.content)
        elif message.role is MessageRole.TOOL:
            _append_turn(
                "user",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": message.tool_call_id,
                        "content": [{"type": "text", "text": message.content or ""}],
                    },
                ],
            )
        elif message.role is MessageRole.ASSISTANT:
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": json.loads(call.arguments or "{}"),
                    },
                )
            _append_turn("assistant", blocks)
        else:
            _append_turn("user", [{"type": "text", "text": message.content or ""}])
    return "\n\n".join(system_parts), turns


def _map_status_error(error: APIStatusError) -> ProviderError:
    """Map an HTTP-level SDK error to the typed hierarchy."""
    provider = "anthropic"
    status = error.status_code
    retry_after: float | None = None
    if error.response is not None:
        header = error.response.headers.get("retry-after")
        if header is not None and header.replace(".", "", 1).isdigit():
            retry_after = float(header)
    if isinstance(error, (AuthenticationError, PermissionDeniedError)):
        return ProviderAuthError("provider rejected credentials", provider=provider)
    if isinstance(error, RateLimitError):
        return ProviderRateLimitError(
            "provider rate limit reached",
            provider=provider,
            retry_after=retry_after,
        )
    if isinstance(error, OverloadedError) or (status is not None and status >= 500):
        return ProviderOverloadedError(f"provider unavailable (HTTP {status})", provider=provider)
    if isinstance(error, (BadRequestError, UnprocessableEntityError, AnthropicNotFoundError)):
        return ProviderRequestError(
            f"provider rejected the request (HTTP {status})",
            provider=provider,
        )
    return ProviderResponseError(f"unexpected provider response (HTTP {status})", provider=provider)
