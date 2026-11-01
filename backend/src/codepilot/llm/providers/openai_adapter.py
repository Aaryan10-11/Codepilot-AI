"""OpenAI Chat Completions adapter.

All ``openai`` SDK types stay inside this module. The DeepSeek adapter
reuses this class because DeepSeek serves the same wire protocol.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    BadRequestError,
    InternalServerError,
    PermissionDeniedError,
    UnprocessableEntityError,
)
from openai import (
    NotFoundError as OpenAINotFoundError,
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
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "function_call": FinishReason.TOOL_CALLS,
    "tool_calls": FinishReason.TOOL_CALLS,
    "content_filter": FinishReason.CONTENT_FILTER,
}


class OpenAICompatibleProvider:
    """Adapter for any OpenAI Chat Completions compatible endpoint."""

    def __init__(
        self,
        *,
        provider_id: ProviderId = ProviderId.OPENAI,
        api_key: SecretStr | str,
        default_model: str,
        base_url: str | None = None,
        timeout_seconds: float = 180.0,
        capabilities: ProviderCapabilities | None = None,
        http_client: Any = None,
        include_stream_usage: bool = True,
    ) -> None:
        """Build the adapter around one ``AsyncOpenAI`` client.

        The SDK's internal retries are disabled on purpose: the project-level
        resilience layer owns retry policy so behavior stays uniform across
        providers.

        Args:
            provider_id: Which provider this adapter talks to.
            api_key: Secret already resolved from settings/environment.
            default_model: Model used when a request does not name one.
            base_url: Optional endpoint override.
            timeout_seconds: Per-call HTTP deadline.
            capabilities: Override for the advertised capability set.
            http_client: SDK-format async HTTP client; tests inject a
                transport-backed client here. Production passes ``None``.
            include_stream_usage: Whether ``stream_options.include_usage`` is
                requested for streaming calls.
        """
        self._provider_id = provider_id
        self._default_model = default_model
        self._include_stream_usage = include_stream_usage
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
        self._client = AsyncOpenAI(**client_kwargs)

    @property
    def provider_id(self) -> ProviderId:
        """Which provider this adapter represents."""
        return self._provider_id

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
            response = await self._client.chat.completions.create(**params)
        except APIStatusError as error:
            raise _map_status_error(error, self.provider_id.value) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error

        if not response.choices:
            raise ProviderResponseError(
                "provider returned no choices",
                provider=self.provider_id.value,
            )
        choice = response.choices[0]
        message = choice.message
        tool_calls = [
            ToolCall(
                id=call.id or f"{self.provider_id.value}-{index}",
                name=call.function.name if call.function else "unknown",
                arguments=call.function.arguments
                if call.function and call.function.arguments
                else "{}",
            )
            for index, call in enumerate(message.tool_calls or [])
        ]
        usage = None
        if response.usage is not None:
            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens or 0,
                output_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens,
            )
        return CompletionResult(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=_FINISH_REASONS.get(choice.finish_reason, FinishReason.OTHER),
            usage=usage,
            model=response.model,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Stream normalized events ending with ``message_end``."""
        params = self._base_params(request)
        params["stream"] = True
        if self._include_stream_usage:
            params["stream_options"] = {"include_usage": True}
        try:
            response_stream = await self._client.chat.completions.create(**params)
        except APIStatusError as error:
            raise _map_status_error(error, self.provider_id.value) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error

        yield MessageStartEvent()
        finish_reason: FinishReason | None = None
        usage: TokenUsage | None = None
        model: str | None = None
        try:
            async for chunk in response_stream:
                if chunk.usage is not None:
                    usage = TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens or 0,
                        output_tokens=chunk.usage.completion_tokens or 0,
                        total_tokens=chunk.usage.total_tokens,
                    )
                if chunk.model:
                    model = chunk.model
                for choice in chunk.choices:
                    if choice.finish_reason is not None:
                        finish_reason = _FINISH_REASONS.get(
                            choice.finish_reason, FinishReason.OTHER
                        )
                    delta = choice.delta
                    if delta.content:
                        yield TextDeltaEvent(text=delta.content)
                    for tool_update in delta.tool_calls or []:
                        function = tool_update.function
                        yield ToolCallDeltaEvent(
                            index=tool_update.index,
                            id=tool_update.id,
                            name=function.name if function else None,
                            arguments_delta=function.arguments or "" if function else "",
                        )
        except APIStatusError as error:
            raise _map_status_error(error, self.provider_id.value) from error
        except APITimeoutError as error:
            raise self._timeout_error() from error
        except APIConnectionError as error:
            raise self._connection_error() from error
        yield MessageEndEvent(
            finish_reason=finish_reason or FinishReason.OTHER,
            usage=usage,
            model=model or self._default_model,
        )

    async def verify(self) -> None:
        """Confirm credentials with one cheap authenticated request."""
        try:
            await self._client.models.list()
        except APIStatusError as error:
            raise _map_status_error(error, self.provider_id.value) from error
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
        """Translate a domain request into SDK parameters."""
        params: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": [self._translate_message(message) for message in request.messages],
        }
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.top_p is not None:
            params["top_p"] = request.top_p
        if request.max_output_tokens is not None:
            params["max_tokens"] = request.max_output_tokens
        if request.stop_sequences:
            params["stop"] = request.stop_sequences
        if request.tools and request.tool_choice is not ToolChoice.NONE:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in request.tools
            ]
            params["tool_choice"] = _translate_tool_choice(request.tool_choice)
        return params

    @staticmethod
    def _translate_message(message: Message) -> dict[str, Any]:
        """Convert one domain message into Chat Completions wire format."""
        if message.role is MessageRole.TOOL:
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content or "",
            }
        if message.tool_calls:
            return {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    }
                    for call in message.tool_calls
                ],
            }
        return {"role": message.role.value, "content": message.content or ""}


def _translate_tool_choice(choice: ToolChoice | None) -> str:
    """Map the domain tool choice to the OpenAI keyword."""
    if choice is ToolChoice.REQUIRED:
        return "required"
    return "auto"


def _map_status_error(error: APIStatusError, provider: str) -> ProviderError:
    """Map an HTTP-level SDK error to the typed hierarchy."""
    status = error.status_code
    retry_after: float | None = None
    if error.response is not None:
        header = error.response.headers.get("retry-after")
        if header is not None and header.replace(".", "", 1).isdigit():
            retry_after = float(header)
    if status == 401 or status == 403:
        return ProviderAuthError("provider rejected credentials", provider=provider)
    if status == 429:
        return ProviderRateLimitError(
            "provider rate limit reached",
            provider=provider,
            retry_after=retry_after,
        )
    if isinstance(error, InternalServerError) or (status is not None and status >= 500):
        return ProviderOverloadedError(f"provider unavailable (HTTP {status})", provider=provider)
    if isinstance(
        error,
        (BadRequestError, UnprocessableEntityError, OpenAINotFoundError, PermissionDeniedError),
    ):
        return ProviderRequestError(
            f"provider rejected the request (HTTP {status})",
            provider=provider,
        )
    return ProviderResponseError(f"unexpected provider response (HTTP {status})", provider=provider)
