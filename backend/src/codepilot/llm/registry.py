"""Ownership of configured LLM providers for the process lifetime.

The registry is created by the application container, exposes configured
state without secrets, and builds provider instances lazily so that listing
providers never constructs SDK clients.
"""

from __future__ import annotations

from typing import Protocol

import structlog

from codepilot.config.settings import LLMSettings
from codepilot.errors import DependencyUnavailableError, NotFoundError
from codepilot.llm.contracts import LLMProvider
from codepilot.llm.credentials import resolve_api_key
from codepilot.llm.errors import ProviderNotConfiguredError
from codepilot.llm.providers import build_provider
from codepilot.llm.resilience import RetryingProvider
from codepilot.models.llm import ProviderId, ProviderRecord

logger = structlog.get_logger(__name__)


class ProviderFactory(Protocol):
    """Builds one provider instance from settings."""

    def __call__(self, provider_id: ProviderId, settings: LLMSettings) -> LLMProvider | None:
        """Return the adapter, or ``None`` when the provider is unconfigured."""
        ...


class ProviderRegistry:
    """Lazily instantiates and caches ``LLMProvider`` adapters."""

    def __init__(
        self,
        settings: LLMSettings,
        factory: ProviderFactory | None = None,
    ) -> None:
        """Bind settings and an optional test factory."""
        self._settings = settings
        self._factory = factory or build_provider
        self._instances: dict[ProviderId, LLMProvider] = {}
        self._closed = False

    @property
    def default_provider(self) -> ProviderId:
        """The provider used when a request names none."""
        return self._settings.default_provider

    def describe(self) -> list[ProviderRecord]:
        """Report configured state for every provider, without secrets.

        Returns:
            One record per supported provider, in enum declaration order.
        """
        return [
            ProviderRecord(
                id=provider_id,
                configured=resolve_api_key(provider_id, self._settings.section(provider_id))
                is not None,
                default_model=self._settings.model_for(provider_id),
            )
            for provider_id in ProviderId
        ]

    def is_configured(self, provider_id: ProviderId) -> bool:
        """Check whether a provider has usable credentials."""
        return any(record.id is provider_id and record.configured for record in self.describe())

    def get(self, provider_id: ProviderId) -> LLMProvider:
        """Return the provider instance, building it on first use.

        Raises:
            ProviderNotConfiguredError: No API key is available.
            DependencyUnavailableError: The registry was closed.
        """
        if self._closed:
            raise DependencyUnavailableError("provider registry is closed")
        cached = self._instances.get(provider_id)
        if cached is not None:
            return cached
        if not self.is_configured(provider_id):
            raise ProviderNotConfiguredError(provider_id.value)
        built = self._factory(provider_id, self._settings)
        if built is None:  # pragma: no cover - guarded by is_configured
            raise ProviderNotConfiguredError(provider_id.value)
        wrapped = RetryingProvider.from_settings(self._settings.retry, built)
        self._instances[provider_id] = wrapped
        logger.debug("llm_provider_ready", provider=provider_id.value)
        return wrapped

    def parse(self, provider_id: str) -> ProviderId:
        """Parse a provider identifier from client input.

        Raises:
            NotFoundError: Unknown provider identifier.
        """
        try:
            return ProviderId(provider_id)
        except ValueError as error:
            raise NotFoundError(f"unknown provider '{provider_id}'") from error

    async def verify(self, provider_id: ProviderId) -> None:
        """Run the provider's cheap credential check."""
        provider = self.get(provider_id)
        await provider.verify()

    async def close(self) -> None:
        """Release every constructed provider instance."""
        if self._closed:
            return
        self._closed = True
        instances = list(self._instances.values())
        self._instances.clear()
        for instance in instances:
            try:
                await instance.close()
            except Exception as error:
                logger.warning("llm_provider_close_failed", error=str(error))
        logger.debug("llm_registry_closed")
