"""Infrastructure client lifecycle without real network connections."""

from __future__ import annotations

from codepilot.config.settings import Settings
from codepilot.db.engine import Database
from codepilot.vector_db.client import QdrantDatabase


async def test_database_engine_is_created_lazily_and_disposed(settings: Settings) -> None:
    database = Database(settings.database)

    assert database.engine is not None
    assert database.engine.dialect.name == "postgresql"

    await database.dispose()


async def test_qdrant_client_can_be_closed_without_being_used(settings: Settings) -> None:
    vector_db = QdrantDatabase(settings.vector_db)
    assert vector_db.client is not None

    await vector_db.close()
