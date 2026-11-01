"""Provider construction from settings.

This is the only module that knows which adapter serves which provider
identifier; nothing else in the codebase names vendor classes.
"""

from __future__ import annotations

from codepilot.config.settings import LLMSettings
from codepilot.llm.contracts import LLMProvider
from codepilot.llm.credentials import resolve_api_key
from codepilot.llm.providers.anthropic_adapter import AnthropicProvider
from codepilot.llm.providers.deepseek_adapter import DeepSeekProvider
from codepilot.llm.providers.gemini_adapter import GeminiProvider
from codepilot.llm.providers.openai_adapter import OpenAICompatibleProvider
from codepilot.models.llm import ProviderId

__all__ = ["build_provider"]


def build_provider(provider_id: ProviderId, settings: LLMSettings) -> LLMProvider | None:
    """Return a configured provider instance, or ``None`` when unconfigured.

    Args:
        provider_id: Which provider to build.
        settings: The LLM settings block holding per-provider connection data.

    Returns:
        An adapter bound to the provider endpoint, or ``None`` when no API key
        is available. Callers surface a clean "not configured" condition.
    """
    section = settings.section(provider_id)
    api_key = resolve_api_key(provider_id, section)
    model = settings.model_for(provider_id)
    match provider_id:
        case ProviderId.OPENAI:
            if api_key is None:
                return None
            return OpenAICompatibleProvider(
                provider_id=provider_id,
                api_key=api_key,
                default_model=model,
                base_url=section.base_url,
                timeout_seconds=section.timeout_seconds,
            )
        case ProviderId.DEEPSEEK:
            if api_key is None:
                return None
            return DeepSeekProvider(
                api_key=api_key,
                default_model=model,
                base_url=section.base_url,
                timeout_seconds=section.timeout_seconds,
            )
        case ProviderId.ANTHROPIC:
            if api_key is None:
                return None
            return AnthropicProvider(
                api_key=api_key,
                default_model=model,
                base_url=section.base_url,
                timeout_seconds=section.timeout_seconds,
            )
        case ProviderId.GOOGLE:
            if api_key is None:
                return None
            return GeminiProvider(
                api_key=api_key,
                default_model=model,
                base_url=section.base_url,
                timeout_seconds=section.timeout_seconds,
            )
