"""Composition root: constructs and owns long-lived resources.

Nothing in this project imports a global singleton. The container is created
once during application startup and injected downward through FastAPI
dependencies or explicit constructor arguments.
"""

from __future__ import annotations

import asyncio
import time

import structlog

from codepilot import __version__
from codepilot.config.settings import Settings
from codepilot.db.engine import Database
from codepilot.llm.registry import ProviderRegistry
from codepilot.services.health import HealthService, PostgresProbe, QdrantProbe
from codepilot.vector_db.client import QdrantDatabase

logger = structlog.get_logger(__name__)


class AppContainer:
    """Owns every process-scoped resource.

    Attributes are exposed as read-only properties so that consumers cannot
    replace infrastructure after startup.
    """

    def __init__(self, settings: Settings) -> None:
        """Create infrastructure clients without opening network connections."""
        self._settings = settings
        self._started_at = time.monotonic()
        self._database = Database(settings.database)
        self._vector_db = QdrantDatabase(settings.vector_db)
        self._llm_registry = ProviderRegistry(settings.llm)
        self._health_service = HealthService(
            probes=(
                PostgresProbe(self._database),
                QdrantProbe(self._vector_db),
            ),
            version=__version__,
            environment=settings.environment.value,
            timeout_seconds=settings.server.health_timeout_seconds,
            started_at=self._started_at,
        )

    @property
    def settings(self) -> Settings:
        """Resolved application settings."""
        return self._settings

    @property
    def database(self) -> Database:
        """PostgreSQL engine owner."""
        return self._database

    @property
    def vector_db(self) -> QdrantDatabase:
        """Qdrant client owner."""
        return self._vector_db

    @property
    def llm_registry(self) -> ProviderRegistry:
        """Ownership of configured LLM providers."""
        return self._llm_registry

    @property
    def health_service(self) -> HealthService:
        """Readiness service used by the health router."""
        return self._health_service

    async def startup(self) -> None:
        """Log startup; resource creation happens eagerly but performs no I/O."""
        logger.info(
            "application_starting",
            version=__version__,
            environment=self._settings.environment.value,
        )

    async def shutdown(self) -> None:
        """Release infrastructure resources, tolerating individual failures."""
        results = await asyncio.gather(
            self._database.dispose(),
            self._vector_db.close(),
            self._llm_registry.close(),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("shutdown_step_failed", error=str(result))
        logger.info("application_stopped")
