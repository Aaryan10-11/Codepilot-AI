"""Typed errors for the LLM layer.

Every adapter maps its vendor exceptions into this hierarchy before they cross
the boundary, so callers never see vendor types. ``retryable`` drives the
resilience wrapper; the other attributes follow the shared ``CodePilotError``
envelope used by the API.
"""

from __future__ import annotations

from http import HTTPStatus

from codepilot.errors import CodePilotError, ConfigurationError


class ProviderError(CodePilotError):
    """Base class for failures talking to an LLM provider.

    Attributes:
        retryable: Whether the resilience layer may retry this failure.
        retry_after: Server-requested delay in seconds, when advertised.
    """

    code = "llm_provider_error"
    http_status = HTTPStatus.BAD_GATEWAY

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retryable: bool = False,
        retry_after: float | None = None,
        **kwargs: object,
    ) -> None:
        """Create a provider failure tagged with the provider identifier."""
        super().__init__(message, details={"provider": provider, **kwargs})
        self.retryable = retryable
        self.retry_after = retry_after


class ProviderAuthError(ProviderError):
    """The provider rejected authentication or authorization."""

    code = "llm_auth_failed"


class ProviderRequestError(ProviderError):
    """The provider rejected the request payload itself.

    This always indicates a CodePilot bug or an unsupported feature; it is
    never retried as-is.
    """

    code = "llm_invalid_request"


class ProviderRateLimitError(ProviderError):
    """The provider throttled the request."""

    code = "llm_rate_limited"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE

    def __init__(self, message: str, *, provider: str, retry_after: float | None = None) -> None:
        """Rate limit errors are transient; ``retry_after`` is honoured."""
        super().__init__(message, provider=provider, retryable=True, retry_after=retry_after)


class ProviderOverloadedError(ProviderError):
    """The provider is temporarily overloaded."""

    code = "llm_overloaded"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE

    def __init__(self, message: str, *, provider: str) -> None:
        """Overload failures are retried with backoff."""
        super().__init__(message, provider=provider, retryable=True)


class ProviderTimeoutError(ProviderError):
    """The provider did not answer within the deadline."""

    code = "llm_timeout"
    http_status = HTTPStatus.GATEWAY_TIMEOUT

    def __init__(self, message: str, *, provider: str) -> None:
        """Timeouts are retried unless the caller's budget is exhausted."""
        super().__init__(message, provider=provider, retryable=True)


class ProviderConnectionError(ProviderError):
    """The provider endpoint could not be reached."""

    code = "llm_connection_failed"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE

    def __init__(self, message: str, *, provider: str) -> None:
        """Connection failures are treated as transient."""
        super().__init__(message, provider=provider, retryable=True)


class ProviderResponseError(ProviderError):
    """The provider answered, but with something we cannot interpret."""

    code = "llm_invalid_response"


class ProviderNotConfiguredError(ConfigurationError):
    """A provider was requested but has no API key configured."""

    code = "llm_provider_not_configured"

    def __init__(self, provider: str) -> None:
        """Name the provider so operators can fix their configuration."""
        super().__init__(
            f"provider '{provider}' is not configured: no API key available",
            details={"provider": provider},
        )
