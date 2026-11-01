"""API key resolution for LLM providers.

Explicit ``CODEPILOT_LLM__<PROVIDER>__API_KEY`` configuration wins. As a
convenience — and to match every provider's own SDK ecosystem — the documented
fallback variables are also honoured. Keys are never logged or serialized.
"""

from __future__ import annotations

import os

import structlog
from pydantic import SecretStr

from codepilot.config.settings import ProviderSettings
from codepilot.models.llm import ProviderId

logger = structlog.get_logger(__name__)

# Documented per-vendor variable names, consulted in order.
_ENV_FALLBACKS: dict[ProviderId, tuple[str, ...]] = {
    ProviderId.OPENAI: ("OPENAI_API_KEY",),
    ProviderId.ANTHROPIC: ("ANTHROPIC_API_KEY",),
    ProviderId.GOOGLE: ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    ProviderId.DEEPSEEK: ("DEEPSEEK_API_KEY",),
}


def resolve_api_key(
    provider_id: ProviderId,
    settings: ProviderSettings,
    *,
    environ: dict[str, str] | None = None,
) -> SecretStr | None:
    """Return the configured API key for a provider, or ``None``.

    Args:
        provider_id: The provider whose key is requested.
        settings: That provider's configuration block.
        environ: Environment mapping to consult; defaults to ``os.environ``.
            The parameter exists for tests, which must not mutate real state.

    Returns:
        The key if the provider is configured. Explicit configuration always
        wins over the environment fallback.
    """
    if settings.api_key is not None:
        return settings.api_key
    source = environ if environ is not None else os.environ
    for variable in _ENV_FALLBACKS[provider_id]:
        value = source.get(variable)
        if value:
            logger.debug(
                "llm_api_key_from_env",
                provider=provider_id.value,
                variable=variable,
            )
            return SecretStr(value)
    return None
