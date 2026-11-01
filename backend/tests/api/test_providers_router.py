"""Provider endpoints over the ASGI transport."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import SecretStr

from codepilot.api.deps import get_llm_registry
from codepilot.app import create_app
from codepilot.config.settings import LLMSettings, ProviderSettings, Settings
from codepilot.models.llm import ProviderId
from tests.unit.llm.fakes import ScriptedProvider


def _app(settings: Settings | None = None, registry: Any = None) -> FastAPI:
    app = create_app(settings or _settings())
    if registry is not None:
        app.dependency_overrides[get_llm_registry] = lambda: registry
    return app


def _settings(**llm: Any) -> Settings:
    return Settings(_env_file=None, llm=LLMSettings(**llm))


class ScriptedRegistry:
    """Registry double that routes a single scripted provider."""

    def __init__(self, provider_id: ProviderId = ProviderId.OPENAI) -> None:
        self.provider = ScriptedProvider(provider_id=provider_id)
        self.configured_ids: frozenset[ProviderId] = frozenset({provider_id})
        self.default: ProviderId = ProviderId.OPENAI

    @property
    def default_provider(self) -> ProviderId:
        return self.default

    def parse(self, provider_id: str) -> ProviderId:
        try:
            return ProviderId(provider_id)
        except ValueError as error:
            from codepilot.llm.errors import ProviderRequestError

            raise ProviderRequestError(
                f"unknown provider '{provider_id}'",
                provider=provider_id,
            ) from error

    def is_configured(self, provider_id: ProviderId) -> bool:
        return provider_id in self.configured_ids

    async def verify(self, provider_id: ProviderId) -> None:
        await self.provider.verify()


async def test_lists_all_providers_with_configuration_state(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(_settings())

    async with LifespanManager(app), client_factory(app) as client:
        response = await client.get("/v1/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_provider"] == "openai"
    assert [provider["id"] for provider in payload["providers"]] == [
        "openai",
        "anthropic",
        "google",
        "deepseek",
    ]
    assert all(provider["configured"] is False for provider in payload["providers"])


async def test_lists_configured_providers_from_keys(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(
        _settings(
            openai=ProviderSettings(api_key=SecretStr("sk-a")),
            google=ProviderSettings(api_key=SecretStr("g-b")),
        ),
    )

    async with LifespanManager(app), client_factory(app) as client:
        response = await client.get("/v1/providers")

    configured = {
        provider["id"]: provider["configured"] for provider in response.json()["providers"]
    }
    assert configured == {
        "openai": True,
        "anthropic": False,
        "google": True,
        "deepseek": False,
    }


async def test_verify_unconfigured_provider_is_not_found(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(_settings())

    async with LifespanManager(app), client_factory(app) as client:
        response = await client.post("/v1/providers/deepseek/verify")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_verify_rejects_unknown_provider(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    app = _app(_settings())

    async with LifespanManager(app), client_factory(app) as client:
        response = await client.post("/v1/providers/bart/verify")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["message"].startswith("unknown provider")


async def test_verify_success_reports_latency(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    registry = ScriptedRegistry()

    async with client_factory(_app(registry=registry)) as client:
        response = await client.post("/v1/providers/openai/verify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_id"] == "openai"
    assert payload["status"] == "ok"
    assert payload["latency_ms"] >= 0
    assert registry.provider.verify_calls == 1


async def test_verify_failure_maps_provider_errors(
    client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    from codepilot.llm.errors import ProviderAuthError

    registry = ScriptedRegistry()
    registry.provider = ScriptedProvider(
        provider_id=ProviderId.OPENAI,
        verify_error=ProviderAuthError("bad key", provider="openai"),
    )

    async with client_factory(_app(registry=registry)) as client:
        response = await client.post("/v1/providers/openai/verify")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_auth_failed"
