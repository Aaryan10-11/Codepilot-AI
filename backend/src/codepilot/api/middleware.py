"""Request correlation and access logging as pure ASGI middleware.

Implemented without ``BaseHTTPMiddleware`` to keep context variables and
streaming responses (SSE, added in a later milestone) correct.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from codepilot.api.errors import internal_error_response

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_HEADER = "X-Request-ID"


class CorrelationMiddleware:
    """Attach a request ID to logs, response headers and ``request.state``.

    The middleware also converts otherwise-unhandled exceptions into the public
    error envelope. Starlette's ``ServerErrorMiddleware`` sits *outside* the
    user middleware stack, so letting it render 500s would drop the correlation
    header entirely; catching here keeps every response traceable.
    """

    def __init__(self, app: ASGIApp, *, mask_unexpected_errors: bool = True) -> None:
        """Wrap an ASGI application.

        Args:
            app: The downstream ASGI application.
            mask_unexpected_errors: Convert unhandled exceptions into the public
                error envelope. Disabled in debug mode to preserve tracebacks.
        """
        self._app = app
        self._mask_unexpected_errors = mask_unexpected_errors

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one ASGI connection."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = self._resolve_request_id(scope)
        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state["request_id"] = request_id

        status_code = 500
        response_started = False
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = int(message["status"])
                MutableHeaders(scope=message)[_HEADER] = request_id
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self._app(scope, receive, send_wrapper)
            except Exception as exc:
                if response_started or not self._mask_unexpected_errors:
                    raise
                response = internal_error_response(Request(scope), exc)
                await response(scope, receive, send_wrapper)
            finally:
                self._log_request(
                    scope=scope,
                    status_code=status_code,
                    duration_ms=(time.perf_counter() - start) * 1000,
                )

    @staticmethod
    def _resolve_request_id(scope: Scope) -> str:
        candidate = Headers(scope=scope).get(_HEADER)
        if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate
        return uuid.uuid4().hex

    @staticmethod
    def _log_request(*, scope: Scope, status_code: int, duration_ms: float) -> None:
        method = str(scope.get("method", ""))
        path = str(scope.get("path", ""))
        payload: dict[str, Any] = {
            "method": method,
            "path": path,
            "status": status_code,
            "duration_ms": round(duration_ms, 2),
        }
        if status_code >= 500:
            structlog.get_logger(__name__).error("http_request", **payload)
        elif status_code >= 400:
            structlog.get_logger(__name__).warning("http_request", **payload)
        elif path.startswith("/v1/health"):
            structlog.get_logger(__name__).debug("http_request", **payload)
        else:
            structlog.get_logger(__name__).info("http_request", **payload)
