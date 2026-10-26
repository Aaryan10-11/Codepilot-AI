"""Central mapping from exceptions to the public error envelope.

Every failure path goes through this module so that no stack trace or internal
detail ever reaches a client.
"""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from codepilot.api.schemas.errors import ErrorDetail, ErrorResponse
from codepilot.errors import CodePilotError

logger = structlog.get_logger(__name__)

_HTTP_ERROR_CODES: dict[int, str] = {
    HTTPStatus.BAD_REQUEST: "bad_request",
    HTTPStatus.UNAUTHORIZED: "unauthenticated",
    HTTPStatus.FORBIDDEN: "forbidden",
    HTTPStatus.NOT_FOUND: "not_found",
    HTTPStatus.METHOD_NOT_ALLOWED: "method_not_allowed",
    HTTPStatus.CONFLICT: "conflict",
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    HTTPStatus.UNPROCESSABLE_ENTITY: "validation_error",
    HTTPStatus.TOO_MANY_REQUESTS: "rate_limited",
}

_INTERNAL_MESSAGE = "An unexpected error occurred."


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return str(value) if value else "-"


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    envelope = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=dict(details or {})),
        request_id=_request_id(request),
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers=dict(headers) if headers else None,
    )


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, CodePilotError):
        return _handle_unexpected(request, exc)
    if exc.http_status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        logger.error(
            "request_failed",
            code=exc.code,
            status=exc.http_status,
            details=exc.details,
            exc_info=exc,
        )
    else:
        logger.warning("request_rejected", code=exc.code, status=exc.http_status)
    return _error_response(
        request,
        status_code=exc.http_status,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return _handle_unexpected(request, exc)
    fields = [
        {
            "location": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    logger.info("request_validation_failed", field_count=len(fields))
    return _error_response(
        request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed.",
        details={"fields": fields},
    )


async def _handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return _handle_unexpected(request, exc)
    code = _HTTP_ERROR_CODES.get(exc.status_code, f"http_{exc.status_code}")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    if exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        logger.error("http_error", status=exc.status_code, detail=message)
    return _error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=exc.headers,
    )


def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc_info=exc)
    return _error_response(
        request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="internal_error",
        message=_INTERNAL_MESSAGE,
    )


def internal_error_response(request: Request, exc: Exception) -> JSONResponse:
    """Build the masked 500 envelope for middleware-level exception handling."""
    return _handle_unexpected(request, exc)


async def _handle_unexpected_async(request: Request, exc: Exception) -> JSONResponse:
    return _handle_unexpected(request, exc)


def register_exception_handlers(app: FastAPI) -> None:
    """Install all exception handlers on the application."""
    app.add_exception_handler(CodePilotError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_async)
