"""Pydantic schemas for the HTTP error envelope."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Envelope returned for every non-2xx response."""

    error: ErrorDetail
    request_id: str
