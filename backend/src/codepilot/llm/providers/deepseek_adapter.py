"""DeepSeek adapter.

DeepSeek serves the OpenAI Chat Completions wire protocol, so this adapter
reuses ``OpenAICompatibleProvider`` and only changes endpoint defaults.
"""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from codepilot.llm.providers.openai_adapter import OpenAICompatibleProvider
from codepilot.models.llm import ProviderCapabilities, ProviderId

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_CONTEXT_WINDOW_TOKENS = 128_000


class DeepSeekProvider(OpenAICompatibleProvider):
    """Adapter for the DeepSeek Chat/Reasoner endpoints."""

    def __init__(
        self,
        *,
        api_key: SecretStr | str,
        default_model: str,
        base_url: str | None = None,
        timeout_seconds: float = 180.0,
        http_client: Any = None,
    ) -> None:
        """Build the adapter with DeepSeek's endpoint defaults."""
        super().__init__(
            provider_id=ProviderId.DEEPSEEK,
            api_key=api_key,
            default_model=default_model,
            base_url=base_url or _DEEPSEEK_BASE_URL,
            timeout_seconds=timeout_seconds,
            capabilities=ProviderCapabilities(
                context_window_tokens=_CONTEXT_WINDOW_TOKENS,
            ),
            http_client=http_client,
            include_stream_usage=True,
        )
