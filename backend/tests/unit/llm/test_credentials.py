"""API key resolution tests."""

from __future__ import annotations

from pydantic import SecretStr

from codepilot.config.settings import ProviderSettings
from codepilot.llm.credentials import resolve_api_key
from codepilot.models.llm import ProviderId


def test_explicit_config_wins_over_environment() -> None:
    settings = ProviderSettings(api_key=SecretStr("explicit"))

    key = resolve_api_key(
        ProviderId.OPENAI,
        settings,
        environ={"OPENAI_API_KEY": "from-env"},
    )

    assert key is not None
    assert key.get_secret_value() == "explicit"


async def test_environment_fallbacks_cover_every_provider() -> None:
    key = resolve_api_key(
        ProviderId.OPENAI,
        ProviderSettings(),
        environ={"OPENAI_API_KEY": "k1"},
    )
    assert key is not None
    assert key.get_secret_value() == "k1"

    key = resolve_api_key(
        ProviderId.ANTHROPIC,
        ProviderSettings(),
        environ={"ANTHROPIC_API_KEY": "k2"},
    )
    assert key is not None
    assert key.get_secret_value() == "k2"

    key = resolve_api_key(
        ProviderId.GOOGLE,
        ProviderSettings(),
        environ={"GEMINI_API_KEY": "k3"},
    )
    assert key is not None
    assert key.get_secret_value() == "k3"

    key = resolve_api_key(
        ProviderId.GOOGLE,
        ProviderSettings(),
        environ={"GOOGLE_API_KEY": "k4"},
    )
    assert key is not None
    assert key.get_secret_value() == "k4"

    key = resolve_api_key(
        ProviderId.DEEPSEEK,
        ProviderSettings(),
        environ={"DEEPSEEK_API_KEY": "k5"},
    )
    assert key is not None
    assert key.get_secret_value() == "k5"


def test_unconfigured_provider_resolves_to_none() -> None:
    assert resolve_api_key(ProviderId.OPENAI, ProviderSettings(), environ={}) is None


def test_empty_env_value_is_ignored() -> None:
    assert (
        resolve_api_key(ProviderId.OPENAI, ProviderSettings(), environ={"OPENAI_API_KEY": ""})
        is None
    )
