"""Concrete health probes for infrastructure clients."""

from __future__ import annotations

from codepilot.services.health.contracts import Pingable


class PostgresProbe:
    """Readiness probe backed by ``SELECT 1`` against PostgreSQL."""

    def __init__(self, database: Pingable) -> None:
        """Bind the probe to a pingable database client."""
        self._database = database

    @property
    def name(self) -> str:
        """Component name reported in health output."""
        return "postgres"

    @property
    def required(self) -> bool:
        """The service cannot serve requests without PostgreSQL."""
        return True

    async def check(self) -> None:
        """Delegate connectivity verification to the database client."""
        await self._database.ping()


class QdrantProbe:
    """Readiness probe that lists Qdrant collections."""

    def __init__(self, vector_store: Pingable) -> None:
        """Bind the probe to a pingable vector-store client."""
        self._vector_store = vector_store

    @property
    def name(self) -> str:
        """Component name reported in health output."""
        return "qdrant"

    @property
    def required(self) -> bool:
        """Retrieval is unavailable without the vector store."""
        return True

    async def check(self) -> None:
        """Delegate connectivity verification to the vector-store client."""
        await self._vector_store.ping()
