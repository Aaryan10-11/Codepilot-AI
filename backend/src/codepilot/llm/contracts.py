"""The provider-neutral LLM contract.

Adapters implement this protocol; agents depend on it and never on vendor
SDKs. The in-memory fakes in the test suite implement it too, which validates
the contract twice.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from codepilot.models.llm import (
    CompletionRequest,
    CompletionResult,
    ProviderCapabilities,
    ProviderId,
    StreamEvent,
)


@runtime_checkable
class LLMProvider(Protocol):
    """One configured model endpoint."""

    @property
    def provider_id(self) -> ProviderId:
        """Stable provider identifier."""
        ...

    @property
    def default_model(self) -> str:
        """Model used when a request does not name one."""
        ...

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Honest capability report for this provider."""
        ...

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Produce one complete completion, mapping vendor errors."""
        ...

    def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Stream normalized events; the last event is always ``message_end``."""
        ...

    async def verify(self) -> None:
        """Confirm credentials cheaply; raise a typed error on failure."""
        ...

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        ...
