"""Gemini adapter tests against a scripted models-API seam."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from google.genai import errors as genai_errors
from google.genai import types as gtypes

from codepilot.llm.contracts import LLMProvider
from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderOverloadedError,
    ProviderRateLimitError,
    ProviderRequestError,
)
from codepilot.llm.providers.gemini_adapter import GeminiProvider
from codepilot.models.llm import (
    FinishReason,
    Message,
    MessageEndEvent,
    MessageRole,
    StreamEvent,
    TokenUsage,
    ToolCall,
)
from tests.unit.llm.fakes import make_request


async def _iterate_chunks(chunks: list[Any]) -> AsyncIterator[Any]:
    """Yield scripted chunks exactly as the SDK's stream iterator would."""
    for chunk in chunks:
        yield chunk


class FakeGeminiModels:
    """Scripted seam implementing ``GeminiModelsAPI``."""

    def __init__(
        self,
        response: Any = None,
        chunks: list[Any] | None = None,
        error: genai_errors.APIError | None = None,
    ) -> None:
        """Record calls and return scripted payloads."""
        self.calls: list[dict[str, Any]] = []
        self._response = response
        self._chunks = chunks or []
        self._error = error

    async def generate_content(self, *, model: str, contents: list[Any], config: Any) -> Any:
        """Record and return the scripted complete response."""
        self.calls.append({"model": model, "contents": contents, "config": config, "stream": False})
        if self._error is not None:
            raise self._error
        return self._response

    async def generate_content_stream(
        self,
        *,
        model: str,
        contents: list[Any],
        config: Any,
    ) -> AsyncIterator[Any]:
        """Record and return a stream of scripted chunks."""
        self.calls.append({"model": model, "contents": contents, "config": config, "stream": True})
        if self._error is not None:
            raise self._error
        return _iterate_chunks(self._chunks)

    def list(self) -> AsyncIterator[Any]:
        """Serve one fake model for credential verification."""
        self.list_called = True

        async def _iterate() -> AsyncIterator[Any]:
            yield "models/gemini-fake"

        return _iterate()


def text_response() -> gtypes.GenerateContentResponse:
    """One-paragraph answer with usage."""
    return gtypes.GenerateContentResponse(
        candidates=[
            gtypes.Candidate(
                content=gtypes.Content(
                    role="model",
                    parts=[gtypes.Part(text="Ciao"), gtypes.Part(text=" there")],
                ),
                finish_reason=gtypes.FinishReason.STOP,
            )
        ],
        model_version="gemini-fake",
        usage_metadata=gtypes.GenerateContentResponseUsageMetadata(
            prompt_token_count=5,
            candidates_token_count=4,
            total_token_count=9,
        ),
    )


def call_response() -> gtypes.GenerateContentResponse:
    """A single function-call candidate."""
    return gtypes.GenerateContentResponse(
        candidates=[
            gtypes.Candidate(
                content=gtypes.Content(
                    role="model",
                    parts=[
                        gtypes.Part(text="checking"),
                        gtypes.Part(
                            function_call=gtypes.FunctionCall(
                                name="get_weather", args={"city": "Paris"}
                            ),
                        ),
                    ],
                ),
                finish_reason=gtypes.FinishReason.STOP,
            )
        ],
        model_version="gemini-fake",
        usage_metadata=gtypes.GenerateContentResponseUsageMetadata(
            prompt_token_count=7, candidates_token_count=2, total_token_count=9
        ),
    )


def stream_chunks() -> list[gtypes.GenerateContentResponse]:
    """Two text chunks followed by a final usage-bearing chunk."""
    return [
        gtypes.GenerateContentResponse(
            candidates=[
                gtypes.Candidate(
                    content=gtypes.Content(role="model", parts=[gtypes.Part(text="Ciao")]),
                )
            ],
            model_version="gemini-fake",
        ),
        gtypes.GenerateContentResponse(
            candidates=[
                gtypes.Candidate(
                    content=gtypes.Content(role="model", parts=[gtypes.Part(text=" there")]),
                    finish_reason=gtypes.FinishReason.STOP,
                )
            ],
            usage_metadata=gtypes.GenerateContentResponseUsageMetadata(
                prompt_token_count=5, candidates_token_count=4, total_token_count=9
            ),
        ),
    ]


def build_provider(models: FakeGeminiModels, **overrides: Any) -> GeminiProvider:
    """Adapter bound to the scripted seam."""
    from pydantic import SecretStr

    return GeminiProvider(
        api_key=SecretStr("g-test"),
        default_model=overrides.pop("default_model", "gemini-prod"),
        models_api=models,
        **overrides,
    )


async def test_adapter_satisfies_the_contract() -> None:
    assert isinstance(build_provider(FakeGeminiModels()), LLMProvider)


async def test_complete_normalises_response() -> None:
    models = FakeGeminiModels(response=text_response())
    provider = build_provider(models)

    result = await provider.complete(make_request(model="gemini-2.0-flash"))

    assert result.content == "Ciao\n there"
    assert result.finish_reason is FinishReason.STOP
    assert result.usage == TokenUsage(input_tokens=5, output_tokens=4, total_tokens=9)
    assert result.model == "gemini-fake"

    call = models.calls[0]
    assert call["model"] == "gemini-2.0-flash"
    assert call["contents"][0].parts[0].text == "hello"
    assert call["config"].system_instruction is None


async def test_complete_builds_tool_calls() -> None:
    models = FakeGeminiModels(response=call_response())
    provider = build_provider(models)

    result = await provider.complete(make_request())

    call = result.tool_calls[0]
    assert call.name == "get_weather"
    from json import loads

    assert loads(call.arguments) == {"city": "Paris"}


async def test_complete_maps_system_and_sampling() -> None:
    models = FakeGeminiModels(response=text_response())
    provider = build_provider(models)
    request = make_request(
        messages=[
            Message(role=MessageRole.SYSTEM, content="Be terse."),
            Message(role=MessageRole.USER, content="hi"),
        ],
        temperature=0.4,
        max_output_tokens=64,
        stop_sequences=["END"],
    )

    await provider.complete(request)

    config = models.calls[0]["config"]
    assert config.system_instruction == "Be terse."
    assert config.temperature == 0.4
    assert config.max_output_tokens == 64
    assert config.stop_sequences == ["END"]


async def test_complete_translates_tool_results() -> None:
    from google.genai import types as g

    models = FakeGeminiModels(
        response=gtypes.GenerateContentResponse(
            candidates=[
                gtypes.Candidate(
                    content=gtypes.Content(role="model", parts=[gtypes.Part(text="ok")]),
                    finish_reason=g.FinishReason.STOP,
                )
            ]
        ),
    )
    provider = build_provider(models)
    request = make_request(
        messages=[
            Message(role=MessageRole.USER, content="weather?"),
            Message(
                role=MessageRole.ASSISTANT,
                tool_calls=[
                    ToolCall(id="google-get_weather-0", name="get_weather", arguments="{}")
                ],
            ),
            Message(role=MessageRole.TOOL, tool_call_id="google-get_weather-0", content="12C"),
        ],
    )

    await provider.complete(request)

    second = models.calls[0]["contents"][2]
    function_response = second.parts[0].function_response
    assert second.role == "user"
    assert function_response.name == "get_weather"
    assert function_response.response == {"result": "12C"}


async def test_complete_rejects_unresolvable_tool_results() -> None:
    models = FakeGeminiModels(response=text_response())
    provider = build_provider(models)
    request = make_request(
        messages=[
            Message(role=MessageRole.TOOL, tool_call_id="ghost", content="x"),
        ],
    )

    with pytest.raises(ProviderRequestError):
        await provider.complete(request)


async def test_stream_emits_normalized_events() -> None:
    models = FakeGeminiModels(chunks=stream_chunks(), response=None)
    provider = build_provider(models)

    events: list[StreamEvent] = [event async for event in provider.stream(make_request())]

    types = [event.type for event in events]
    assert types == ["message_start", "text_delta", "text_delta", "message_end"]
    end = events[-1]
    assert isinstance(end, MessageEndEvent)
    assert end.finish_reason is FinishReason.STOP
    assert end.usage == TokenUsage(input_tokens=5, output_tokens=4, total_tokens=9)
    assert end.model == "gemini-fake"


def make_client_error(code: int) -> genai_errors.APIError:
    """Build a Gemini ClientError with the given status."""
    response = {"error": {"code": code, "message": "nope"}}
    return genai_errors.ClientError(code, response)


def make_server_error(code: int) -> genai_errors.APIError:
    """Build a Gemini ServerError with the given status."""
    response = {"error": {"code": code, "message": "down"}}
    return genai_errors.ServerError(code, response)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (make_client_error(401), ProviderAuthError),
        (make_client_error(429), ProviderRateLimitError),
        (make_client_error(400), ProviderRequestError),
        (make_server_error(500), ProviderOverloadedError),
    ],
)
async def test_error_mapping(error: genai_errors.APIError, expected: type[Exception]) -> None:
    models = FakeGeminiModels(response=text_response(), error=error)
    provider = build_provider(models)

    with pytest.raises(expected):
        await provider.complete(make_request())


async def test_verify_consumes_a_models_list() -> None:
    models = FakeGeminiModels()
    provider = build_provider(models)

    await provider.verify()

    assert models.list_called is True


async def test_close_is_safe_without_a_real_client() -> None:
    provider = build_provider(FakeGeminiModels())

    await provider.close()  # must not raise
