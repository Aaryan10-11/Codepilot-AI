"""Registry lifecycle tests against scripted providers."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from codepilot.config.settings import LLMSettings, ProviderSettings
from codepilot.errors import DependencyUnavailableError
from codepilot.llm.contracts import LLMProvider
from codepilot.llm.errors import ProviderAuthError, ProviderNotConfiguredError
from codepilot.llm.registry import ProviderFactory, ProviderRegistry
from codepilot.llm.resilience import RetryingProvider
from codepilot.models.llm import ProviderId
from tests.unit.llm.fakes import ScriptedProvider


def configured_settings() -> LLMSettings:
    """Settings with only OpenAI configured."""
    return LLMSettings(
        openai=ProviderSettings(api_key=SecretStr("sk-test")),
    )


def fake_factory(
    instances: dict[ProviderId, ScriptedProvider],
    calls: list[ProviderId] | None = None,
) -> ProviderFactory:
    """Build a factory returning scripted providers; records build calls."""

    def factory(provider_id: ProviderId, settings: LLMSettings) -> LLMProvider | None:
        if calls is not None:
            calls.append(provider_id)
        return instances.get(provider_id)

    return factory


async def test_describe_reports_configuration_without_secrets() -> None:
    registry = ProviderRegistry(configured_settings(), factory=fake_factory({}))

    records = registry.describe()

    by_id = {record.id: record for record in records}
    assert by_id[ProviderId.OPENAI].configured is True
    assert by_id[ProviderId.ANTHROPIC].configured is False
    assert by_id[ProviderId.OPENAI].default_model == "gpt-4.1"
    assert "sk-test" not in str(records)


async def test_describe_honours_env_fallback_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-env-key")
    registry = ProviderRegistry(LLMSettings(), factory=fake_factory({}))

    records = {record.id: record for record in registry.describe()}
    assert records[ProviderId.DEEPSEEK].configured is True


async def test_get_builds_once_and_caches() -> None:
    provider = ScriptedProvider()
    calls: list[ProviderId] = []
    registry = ProviderRegistry(
        configured_settings(),
        factory=fake_factory({ProviderId.OPENAI: provider}, calls),
    )

    first = registry.get(ProviderId.OPENAI)
    second = registry.get(ProviderId.OPENAI)

    assert first is second
    assert isinstance(first, RetryingProvider)
    underlying = first.wrapped
    assert isinstance(underlying, ScriptedProvider)
    assert underlying is provider
    assert calls == [ProviderId.OPENAI]


async def test_get_wraps_provider_with_retry_policy() -> None:
    provider = ScriptedProvider()
    calls: list[ProviderId] = []
    registry = ProviderRegistry(
        configured_settings(),
        factory=fake_factory({ProviderId.OPENAI: provider}, calls),
    )

    resolved = registry.get(ProviderId.OPENAI)

    assert isinstance(resolved, RetryingProvider)


async def test_get_unknown_provider_is_cleanly_rejected() -> None:
    registry = ProviderRegistry(LLMSettings(), factory=fake_factory({}))

    with pytest.raises(ProviderNotConfiguredError):
        registry.get(ProviderId.ANTHROPIC)


async def test_parse_rejects_unknown_identifiers() -> None:
    registry = ProviderRegistry(LLMSettings(), factory=fake_factory({}))

    with pytest.raises(Exception, match="unknown provider"):
        registry.parse("bart")

    assert registry.parse("deepseek") is ProviderId.DEEPSEEK


async def test_verify_forwards_to_provider() -> None:
    provider = ScriptedProvider()
    registry = ProviderRegistry(
        configured_settings(),
        factory=fake_factory({ProviderId.OPENAI: provider}),
    )

    await registry.verify(ProviderId.OPENAI)

    assert provider.verify_calls == 1


async def test_verify_surfaces_auth_failures() -> None:
    provider = ScriptedProvider(verify_error=ProviderAuthError("nope", provider="openai"))
    registry = ProviderRegistry(
        configured_settings(),
        factory=fake_factory({ProviderId.OPENAI: provider}),
    )

    with pytest.raises(ProviderAuthError):
        await registry.verify(ProviderId.OPENAI)


async def test_close_releases_every_instance_and_refuses_reuse() -> None:
    provider = ScriptedProvider()
    registry = ProviderRegistry(
        configured_settings(),
        factory=fake_factory({ProviderId.OPENAI: provider}),
    )
    registry.get(ProviderId.OPENAI)

    await registry.close()

    assert provider.close_calls == 1
    with pytest.raises(DependencyUnavailableError):
        registry.get(ProviderId.OPENAI)


async def test_default_provider_comes_from_settings() -> None:
    settings = LLMSettings(
        default_provider=ProviderId.GOOGLE,
        google=ProviderSettings(api_key=SecretStr("g-key")),
    )
    registry = ProviderRegistry(settings, factory=fake_factory({}))

    assert registry.default_provider is ProviderId.GOOGLE
