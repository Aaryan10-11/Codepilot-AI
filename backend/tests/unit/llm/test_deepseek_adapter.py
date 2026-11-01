"""DeepSeek adapter tests: endpoint defaults on the shared OpenAI adapter."""

from __future__ import annotations

from typing import Any

from httpx2 import ASGITransport
from httpx2 import AsyncClient as HttpxAsyncClient
from pydantic import SecretStr

from codepilot.llm.providers.deepseek_adapter import DeepSeekProvider
from codepilot.models.llm import ProviderId
from tests.unit.llm.fakes import make_request
from tests.unit.llm.wire import FakeOpenAIApp, tool_call_chunks


def build_provider(app: FakeOpenAIApp, **overrides: Any) -> DeepSeekProvider:
    """Construct the adapter with a transport-backed SDK client."""
    return DeepSeekProvider(
        api_key=SecretStr("ds-test"),
        default_model=overrides.pop("default_model", "deepseek-chat"),
        base_url=overrides.pop("base_url", "http://testserver"),
        http_client=HttpxAsyncClient(transport=ASGITransport(app=app), timeout=30.0),
        **overrides,
    )


async def test_reports_deepseek_identity() -> None:
    provider = build_provider(FakeOpenAIApp())

    assert provider.provider_id is ProviderId.DEEPSEEK
    assert provider.default_model == "deepseek-chat"
    assert provider.capabilities.context_window_tokens == 128_000
    assert provider.capabilities.vision is False


async def test_stream_requests_usage_included() -> None:
    app = FakeOpenAIApp()
    app.chunks = tool_call_chunks()
    provider = build_provider(app)

    events: list[Any] = [event async for event in provider.stream(make_request())]

    assert events
    request = app.requests[0]
    assert request["stream"] is True
    assert request["stream_options"] == {"include_usage": True}
    assert request["model"] == "deepseek-chat"


async def test_endpoint_defaults_to_deepseek_host() -> None:
    """Without an override, the SDK client targets the DeepSeek endpoint."""
    provider = DeepSeekProvider(
        api_key=SecretStr("ds-test"),
        default_model="deepseek-chat",
    )

    assert str(provider._client.base_url).rstrip("/") == "https://api.deepseek.com"
