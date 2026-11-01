"""Model provider introspection and credential verification."""

from __future__ import annotations

import time

from fastapi import APIRouter

from codepilot.api.deps import LLMRegistryDep
from codepilot.api.schemas.providers import (
    ProviderListResponse,
    ProviderSummary,
    ProviderVerificationResponse,
)
from codepilot.errors import NotFoundError

router = APIRouter(prefix="/v1", tags=["providers"])


@router.get(
    "/providers",
    response_model=ProviderListResponse,
    summary="List model providers",
    description="Reports which providers are configured and their default models.",
)
async def list_providers(registry: LLMRegistryDep) -> ProviderListResponse:
    """Return the provider catalogue without secrets."""
    records = registry.describe()
    return ProviderListResponse(
        default_provider=registry.default_provider.value,
        providers=[
            ProviderSummary(
                id=record.id.value,
                configured=record.configured,
                default_model=record.default_model,
            )
            for record in records
        ],
    )


@router.post(
    "/providers/{provider_id}/verify",
    response_model=ProviderVerificationResponse,
    summary="Verify provider credentials",
    description=(
        "Performs one cheap authenticated request against the provider and "
        "returns 200 when the credentials work. 404 when unconfigured. "
        "Upstream failures surface the standard error envelope."
    ),
)
async def verify_provider(
    provider_id: str,
    registry: LLMRegistryDep,
) -> ProviderVerificationResponse:
    """Verify one provider's credentials."""
    parsed = registry.parse(provider_id)
    if not registry.is_configured(parsed):
        raise NotFoundError(f"provider '{provider_id}' is not configured")
    started = time.perf_counter()
    await registry.verify(parsed)
    latency_ms = (time.perf_counter() - started) * 1000
    return ProviderVerificationResponse(
        provider_id=parsed.value,
        latency_ms=round(latency_ms, 2),
    )
