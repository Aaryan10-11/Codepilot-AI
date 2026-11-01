"""Response schemas for provider introspection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProviderSummary(BaseModel):
    """One provider as visible to clients; never contains secrets."""

    model_config = ConfigDict(frozen=True)

    id: str
    configured: bool
    default_model: str


class ProviderListResponse(BaseModel):
    """All supported providers and the default selection."""

    model_config = ConfigDict(frozen=True)

    default_provider: str
    providers: list[ProviderSummary] = Field(min_length=1)


class ProviderVerificationResponse(BaseModel):
    """Result of a successful credential check."""

    model_config = ConfigDict(frozen=True)

    provider_id: str
    status: Literal["ok"] = "ok"
    latency_ms: float = Field(ge=0)
