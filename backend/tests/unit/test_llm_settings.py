"""LLM settings parsing and validation."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from codepilot.config.settings import LLMSettings, Settings
from codepilot.models.llm import ProviderId


def test_canonical_default_models_are_filled() -> None:
    settings = LLMSettings()

    assert settings.model_for(ProviderId.OPENAI) == "gpt-4.1"
    assert settings.model_for(ProviderId.ANTHROPIC) == "claude-sonnet-4-5"
    assert settings.model_for(ProviderId.GOOGLE) == "gemini-2.5-flash"
    assert settings.model_for(ProviderId.DEEPSEEK) == "deepseek-chat"


async def test_nested_env_keys_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEPILOT_LLM__OPENAI__API_KEY", "sk-env")
    monkeypatch.setenv("CODEPILOT_LLM__DEFAULT_PROVIDER", "anthropic")
    monkeypatch.setenv("CODEPILOT_LLM__ANTHROPIC__API_KEY", "sk-ant-env")

    settings = Settings(_env_file=None).llm

    assert settings.default_provider is ProviderId.ANTHROPIC
    assert settings.openai.api_key is not None
    assert settings.openai.api_key.get_secret_value() == "sk-env"
    assert settings.anthropic.api_key is not None
    assert settings.anthropic.api_key.get_secret_value() == "sk-ant-env"


async def test_default_provider_must_be_supported() -> None:
    with pytest.raises(ValueError):
        LLMSettings(default_provider="bart")


async def test_timeout_bounds_are_enforced() -> None:
    with pytest.raises(ValueError):
        LLMSettings(
            openai=Settings(_env_file=None).llm.openai.model_copy(update={"timeout_seconds": 0})
        )


async def test_secret_values_never_leak_via_str() -> None:
    settings = LLMSettings(
        openai=Settings(_env_file=None).llm.openai.model_copy(
            update={"api_key": SecretStr("sk-very-secret")},
        )
    )

    assert "sk-very-secret" not in str(settings.model_dump())
