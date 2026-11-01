"""Google Gemini adapter.

All ``google.genai`` types stay inside this module. The adapter binds to the
SDK's ``aio.models`` interface through a narrow protocol so that tests can
supply a fake without patching vendor internals; production wires the real
client in ``__init__``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable
from typing import Any, Protocol, cast

import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as gtypes
from pydantic import SecretStr

from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderOverloadedError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
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
    "FINISH_REASON_UNSPECIFIED": FinishReason.OTHER,
    "STOP": FinishReason.STOP,
    "MAX_TOKENS": FinishReason.LENGTH,
    "SAFETY": FinishReason.CONTENT_FILTER,
    "BLOCKLIST": FinishReason.CONTENT_FILTER,
    "PROHIBITED_CONTENT": FinishReason.CONTENT_FILTER,
    "SPII": FinishReason.CONTENT_FILTER,
    "RECITATION": FinishReason.CONTENT_FILTER,
}


class GeminiModelsAPI(Protocol):
    """The slice of ``client.aio.models`` this adapter needs.

    Tests implement this protocol with scripted responses; the real SDK
    satisfies it structurally.
    """

    def generate_content(
        self,
        *,
        model: str,
        contents: list[Any],
        config: Any,
    ) -> Awaitable[Any]:
        """Generate one completion."""
        ...

    def generate_content_stream(
        self,
        *,
        model: str,
        contents: list[Any],
        config: Any,
    ) -> Awaitable[AsyncIterator[Any]]:
        """Generate a stream of chunks."""
        ...

    def list(self) -> AsyncIterator[Any]:
        """List available models; the real SDK returns an async pager."""
        ...


class GeminiProvider:
    """Adapter for the Gemini generateContent endpoints."""

    def __init__(
        self,
        *,
        api_key: SecretStr | str,
        default_model: str,
        base_url: str | None = None,
        timeout_seconds: float = 180.0,
        capabilities: ProviderCapabilities | None = None,
        models_api: GeminiModelsAPI | None = None,
    ) -> None:
        """Build the adapter, or bind a supplied models API for tests.

        Args:
            api_key: Secret already resolved from settings/environment.
            default_model: Model used when a request does not name one.
            base_url: Optional endpoint override (Gemini AI Studio default).
            timeout_seconds: Per-call HTTP deadline.
            capabilities: Override for the advertised capability set.
            models_api: Injected seam; production constructs the real client.
        """
        self._default_model = default_model
        self._capabilities = capabilities or ProviderCapabilities()
        self._client: Any = None
        if models_api is not None:
            self._models = models_api
            return
        options = gtypes.HttpOptions(timeout=int(timeout_seconds * 1000))
        if base_url is not None:
            options = gtypes.HttpOptions(base_url=base_url, timeout=int(timeout_seconds * 1000))
        key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else str(api_key)
        client = genai.Client(api_key=key, http_options=options)
        self._client = client
        self._models = cast(GeminiModelsAPI, client.aio.models)

    @property
    def provider_id(self) -> ProviderId:
        """Gemini's stable identifier."""
        return ProviderId.GOOGLE

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
        contents, config = self._build_payload(request)
        try:
            response = await self._models.generate_content(
                model=self._model_name(request),
                contents=contents,
                config=config,
            )
        except genai_errors.APIError as error:
            raise _map_genai_error(error) from error
        return _map_response(request.messages, response)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Stream normalized events ending with ``message_end``."""
        contents, config = self._build_payload(request)
        try:
            chunks = await self._models.generate_content_stream(
                model=self._model_name(request),
                contents=contents,
                config=config,
            )
        except genai_errors.APIError as error:
            raise _map_genai_error(error) from error

        yield MessageStartEvent()
        finish_reason: FinishReason | None = None
        usage: TokenUsage | None = None
        tool_index = 0
        model: str | None = None
        try:
            async for chunk in chunks:
                model = chunk.model_version or model
                if chunk.usage_metadata is not None:
                    usage = _map_usage(chunk.usage_metadata)
                if not chunk.candidates:
                    continue
                candidate = chunk.candidates[0]
                if candidate.finish_reason is not None:
                    finish_reason = _FINISH_REASONS.get(
                        candidate.finish_reason.name, FinishReason.OTHER
                    )
                if candidate.content is None:
                    continue
                for part in candidate.content.parts or []:
                    if part.text:
                        yield TextDeltaEvent(text=part.text)
                    elif part.function_call is not None:
                        call = part.function_call
                        yield ToolCallDeltaEvent(
                            index=tool_index,
                            id=f"{self.provider_id.value}-{call.name}-{tool_index}",
                            name=call.name,
                            arguments_delta=json.dumps(dict(call.args or {})),
                        )
                        tool_index += 1
        except genai_errors.APIError as error:
            raise _map_genai_error(error) from error
        yield MessageEndEvent(
            finish_reason=finish_reason or FinishReason.OTHER,
            usage=usage,
            model=model or self._default_model,
        )

    async def verify(self) -> None:
        """Confirm credentials with one cheap models list."""
        try:
            iterator = self._models.list()
        except genai_errors.APIError as error:  # pragma: no cover - rare sync path
            raise _map_genai_error(error) from error
        try:
            async for _ in iterator:
                break
        except genai_errors.APIError as error:
            raise _map_genai_error(error) from error

    async def close(self) -> None:
        """Release the underlying HTTP client when we constructed it."""
        client = self._client
        if client is not None:
            client.close()

    def _model_name(self, request: CompletionRequest) -> str:
        """Resolve the model, Gemini models are qualified names."""
        chosen = request.model or self._default_model
        return chosen if "/" in chosen or "." in chosen else f"models/{chosen}"

    def _build_payload(
        self,
        request: CompletionRequest,
    ) -> tuple[list[gtypes.Content], gtypes.GenerateContentConfig]:
        """Translate the domain request into Gemini contents and config."""
        tool_names = _tool_name_lookup(request.messages)
        contents: list[gtypes.Content] = []
        system_parts: list[str] = []
        for message in request.messages:
            if message.role is MessageRole.SYSTEM:
                if message.content:
                    system_parts.append(message.content)
            elif message.role is MessageRole.TOOL:
                name = message.name or tool_names.get(message.tool_call_id or "")
                if not name:
                    raise ProviderRequestError(
                        "tool result must reference a known tool call",
                        provider=self.provider_id.value,
                    )
                contents.append(
                    gtypes.Content(
                        role="user",
                        parts=[
                            gtypes.Part(
                                function_response=gtypes.FunctionResponse(
                                    name=name,
                                    response={"result": message.content or ""},
                                ),
                            ),
                        ],
                    ),
                )
            else:
                role = "model" if message.role is MessageRole.ASSISTANT else "user"
                parts: list[gtypes.Part] = []
                if message.content:
                    parts.append(gtypes.Part(text=message.content))
                if message.tool_calls:
                    for call in message.tool_calls:
                        parts.append(
                            gtypes.Part(
                                function_call=gtypes.FunctionCall(
                                    name=call.name,
                                    args=json.loads(call.arguments or "{}"),
                                ),
                            ),
                        )
                contents.append(gtypes.Content(role=role, parts=parts))
        config = gtypes.GenerateContentConfig()
        if system_parts:
            config.system_instruction = "\n\n".join(system_parts)
        if request.temperature is not None:
            config.temperature = request.temperature
        if request.top_p is not None:
            config.top_p = request.top_p
        if request.max_output_tokens is not None:
            config.max_output_tokens = request.max_output_tokens
        if request.stop_sequences:
            config.stop_sequences = request.stop_sequences
        if request.tools and request.tool_choice is not ToolChoice.NONE:
            config.tools = [
                gtypes.Tool(
                    function_declarations=[
                        gtypes.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters_json_schema=tool.parameters,
                        )
                        for tool in request.tools
                    ],
                ),
            ]
            config.tool_config = gtypes.ToolConfig(
                function_calling_config=gtypes.FunctionCallingConfig(
                    mode=(
                        gtypes.FunctionCallingConfigMode.ANY
                        if request.tool_choice is ToolChoice.REQUIRED
                        else gtypes.FunctionCallingConfigMode.AUTO
                    ),
                ),
            )
        return contents, config


def _tool_name_lookup(messages: list[Message]) -> dict[str, str]:
    """Build a tool-call id to tool name map from assistant turns."""
    lookup: dict[str, str] = {}
    for message in messages:
        for call in message.tool_calls:
            lookup[call.id] = call.name
    return lookup


def _map_response(messages: list[Message], response: Any) -> CompletionResult:
    """Normalize a ``GenerateContentResponse``."""
    if not response.candidates:
        raise ProviderResponseError(
            "provider returned no candidates",
            provider=ProviderId.GOOGLE.value,
        )
    candidate = response.candidates[0]
    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    if candidate.content is not None:
        for index, part in enumerate(candidate.content.parts or []):
            if part.text:
                content_parts.append(part.text)
            elif part.function_call is not None:
                call = part.function_call
                tool_calls.append(
                    ToolCall(
                        id=f"{ProviderId.GOOGLE.value}-{call.name}-{index}",
                        name=call.name,
                        arguments=json.dumps(dict(call.args or {})),
                    ),
                )
    finish_name = candidate.finish_reason.name if candidate.finish_reason is not None else None
    return CompletionResult(
        content="\n".join(content_parts) if content_parts else None,
        tool_calls=tool_calls,
        finish_reason=_FINISH_REASONS.get(finish_name, FinishReason.OTHER),
        usage=_map_usage(response.usage_metadata) if response.usage_metadata is not None else None,
        model=getattr(response, "model_version", None),
    )


def _map_usage(metadata: Any) -> TokenUsage:
    """Normalize Gemini usage metadata across SDK revisions."""
    prompt = metadata.prompt_token_count or 0
    output = (
        getattr(metadata, "candidates_token_count", None)
        or getattr(metadata, "response_token_count", None)
        or 0
    )
    total = metadata.total_token_count
    if total is None:
        total = prompt + output
    return TokenUsage(input_tokens=prompt, output_tokens=output, total_tokens=total)


def _map_genai_error(error: genai_errors.APIError) -> ProviderError:
    """Map a Gemini SDK error to the typed hierarchy."""
    provider = "google"
    status = error.code
    if status in (401, 403):
        return ProviderAuthError("provider rejected credentials", provider=provider)
    if status == 429:
        return ProviderRateLimitError("provider rate limit reached", provider=provider)
    if status is not None and status >= 500:
        return ProviderOverloadedError(f"provider unavailable (HTTP {status})", provider=provider)
    if isinstance(error, genai_errors.ServerError):
        return ProviderOverloadedError("provider unavailable", provider=provider)
    if isinstance(error, genai_errors.ClientError):
        return ProviderRequestError(
            f"provider rejected the request (HTTP {status})",
            provider=provider,
        )
    # Unknown error shapes (including network failures without a status).
    return ProviderConnectionError("could not reach provider", provider=provider)
