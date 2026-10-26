"""Configuration parsing and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from codepilot.config.settings import (
    DatabaseSettings,
    Environment,
    QdrantSettings,
    ServerSettings,
    Settings,
)


def test_defaults_are_development_ready() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "CodePilot AI"
    assert settings.environment is Environment.DEVELOPMENT
    assert settings.debug is False
    assert settings.server.port == 8000
    assert settings.server.health_timeout_seconds == 2.0
    assert settings.logging.level == "INFO"
    assert settings.logging.format == "console"


def test_nested_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEPILOT_SERVER__PORT", "9100")
    monkeypatch.setenv("CODEPILOT_LOGGING__LEVEL", "DEBUG")
    monkeypatch.setenv("CODEPILOT_ENVIRONMENT", "test")

    settings = Settings(_env_file=None)

    assert settings.server.port == 9100
    assert settings.logging.level == "DEBUG"
    assert settings.environment is Environment.TEST


def test_database_url_requires_asyncpg_driver() -> None:
    with pytest.raises(ValidationError, match="asyncpg"):
        DatabaseSettings(url="postgresql://user:pass@localhost:5432/db")


def test_database_pool_bounds_are_enforced() -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings(pool_size=0)


def test_qdrant_url_is_normalised() -> None:
    assert QdrantSettings(url="http://localhost:6333/").url == "http://localhost:6333"


def test_qdrant_url_requires_http_scheme() -> None:
    with pytest.raises(ValidationError):
        QdrantSettings(url="localhost:6333")


def test_qdrant_api_key_is_secret() -> None:
    settings = QdrantSettings(api_key="super-secret")
    assert settings.api_key is not None
    assert "super-secret" not in repr(settings)
    assert settings.api_key.get_secret_value() == "super-secret"


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="wildcard CORS"):
        Settings(
            environment=Environment.PRODUCTION,
            server=ServerSettings(cors_origins=["*"]),
            _env_file=None,
        )


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError, match="debug"):
        Settings(environment=Environment.PRODUCTION, debug=True, _env_file=None)


def test_health_timeout_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        ServerSettings(health_timeout_seconds=0)


def test_environment_accepts_production_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEPILOT_ENVIRONMENT", "production")
    monkeypatch.setenv("CODEPILOT_SERVER__CORS_ORIGINS", '["https://app.example.com"]')

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.PRODUCTION
    assert settings.server.cors_origins == ["https://app.example.com"]
