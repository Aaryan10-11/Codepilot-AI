"""Provider-neutral LLM layer.

This package owns the ``LLMProvider`` contract, the typed error hierarchy, the
resilience wrapper, and the adapters. Agents depend on the contract; only
``codepilot.llm.providers`` may import vendor SDKs.
"""

from codepilot.llm.contracts import LLMProvider
from codepilot.llm.errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderOverloadedError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from codepilot.llm.registry import ProviderRegistry
from codepilot.llm.resilience import RetryingProvider, RetryPolicy

__all__ = [
    "LLMProvider",
    "ProviderAuthError",
    "ProviderConnectionError",
    "ProviderError",
    "ProviderNotConfiguredError",
    "ProviderOverloadedError",
    "ProviderRateLimitError",
    "ProviderRegistry",
    "ProviderRequestError",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "RetryPolicy",
    "RetryingProvider",
]
