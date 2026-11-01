"""FastAPI dependency wiring.

Dependencies resolve from ``app.state.container``; tests override individual
providers rather than patching module-level state.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from codepilot.container import AppContainer
from codepilot.llm.registry import ProviderRegistry
from codepilot.services.health import HealthService


def get_container(request: Request) -> AppContainer:
    """Return the container created by the application lifespan."""
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, AppContainer):
        raise RuntimeError("application container is not initialised")
    return container


def get_health_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> HealthService:
    """Expose the readiness service."""
    return container.health_service


def get_llm_registry(
    container: Annotated[AppContainer, Depends(get_container)],
) -> ProviderRegistry:
    """Expose the configured LLM providers."""
    return container.llm_registry


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
LLMRegistryDep = Annotated[ProviderRegistry, Depends(get_llm_registry)]
