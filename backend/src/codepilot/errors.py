"""Typed exception hierarchy shared by every layer.

Transport-agnostic on purpose: the API layer maps these to HTTP status codes so
that services, agents and tools never need to know about HTTP.
"""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any


class CodePilotError(Exception):
    """Base class for all expected, user-facing CodePilot failures."""

    code: str = "internal_error"
    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        """Create an error with a human-readable message and optional metadata."""
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details or {})

    def to_payload(self) -> dict[str, Any]:
        """Return the serialisable representation used in API responses."""
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class ConfigurationError(CodePilotError):
    """Configuration is missing or invalid; the process cannot function."""

    code = "configuration_error"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


class DependencyUnavailableError(CodePilotError):
    """A required backing service (database, vector store, model provider) is down."""

    code = "dependency_unavailable"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE


class NotFoundError(CodePilotError):
    """The requested resource does not exist."""

    code = "not_found"
    http_status = HTTPStatus.NOT_FOUND


class InvalidRequestError(CodePilotError):
    """The request is syntactically valid but semantically rejected."""

    code = "invalid_request"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class AuthenticationError(CodePilotError):
    """The caller could not be authenticated."""

    code = "unauthenticated"
    http_status = HTTPStatus.UNAUTHORIZED


class RateLimitedError(CodePilotError):
    """The caller exceeded an applicable rate limit."""

    code = "rate_limited"
    http_status = HTTPStatus.TOO_MANY_REQUESTS
