"""Async PostgreSQL access owned by the application container."""

from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from codepilot.config.settings import DatabaseSettings

logger = structlog.get_logger(__name__)


class Database:
    """Thin owner of the async SQLAlchemy engine.

    Engine creation performs no I/O; connections are opened lazily so the
    process can start while PostgreSQL is still booting.
    """

    def __init__(self, settings: DatabaseSettings) -> None:
        """Create the async engine; connections are opened lazily."""
        self._settings = settings
        self._engine = create_async_engine(
            settings.url,
            echo=settings.echo,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_pre_ping=True,
            connect_args={
                "timeout": settings.connect_timeout_seconds,
                "server_settings": {"application_name": "codepilot-ai"},
            },
        )

    @property
    def engine(self) -> AsyncEngine:
        """The shared async engine, used by repositories in later milestones."""
        return self._engine

    async def ping(self) -> None:
        """Execute a trivial query; raises if the database is unreachable."""
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        """Close every pooled connection."""
        await self._engine.dispose()
        logger.debug("database_engine_disposed")
