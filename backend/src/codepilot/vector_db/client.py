"""Async Qdrant client ownership.

Collection management and vector operations arrive with the RAG milestone; this
module currently provides the connection lifecycle used by readiness checks.
"""

from __future__ import annotations

import structlog
from qdrant_client import AsyncQdrantClient

from codepilot.config.settings import QdrantSettings

logger = structlog.get_logger(__name__)


class QdrantDatabase:
    """Owns one ``AsyncQdrantClient`` for the process lifetime."""

    def __init__(self, settings: QdrantSettings) -> None:
        """Create the async client; no request is made until first use."""
        self._settings = settings
        self._client = AsyncQdrantClient(
            url=settings.url,
            api_key=settings.api_key.get_secret_value() if settings.api_key else None,
            timeout=int(settings.timeout_seconds),
            prefer_grpc=False,
            check_compatibility=False,
        )

    @property
    def client(self) -> AsyncQdrantClient:
        """The shared client, injected into repositories in later milestones."""
        return self._client

    async def ping(self) -> None:
        """List collections; raises if Qdrant is unreachable."""
        await self._client.get_collections()

    async def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._client.close()
        logger.debug("qdrant_client_closed")
