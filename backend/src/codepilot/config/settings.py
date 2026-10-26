"""Typed, environment-driven application configuration.

All configuration is expressed as nested pydantic models so that wiring code
receives small, validated objects instead of reading ``os.environ`` directly.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment, used to relax or tighten operational defaults."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ServerSettings(BaseModel):
    """HTTP server and CORS configuration."""

    host: str = "0.0.0.0"  # noqa: S104 - container-bound service
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(default_factory=list)
    health_timeout_seconds: float = Field(default=2.0, gt=0, le=30)


class DatabaseSettings(BaseModel):
    """PostgreSQL connection settings."""

    url: str = "postgresql+asyncpg://codepilot:codepilot_dev_password@localhost:5432/codepilot"
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=100)
    echo: bool = False
    connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)

    @field_validator("url")
    @classmethod
    def _require_async_driver(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database url must use the 'postgresql+asyncpg' driver")
        return value


class QdrantSettings(BaseModel):
    """Qdrant vector database connection settings."""

    url: str = "http://localhost:6333"
    api_key: SecretStr | None = None
    timeout_seconds: float = Field(default=5.0, gt=0, le=120)

    @field_validator("url")
    @classmethod
    def _normalise_url(cls, value: str) -> str:
        return str(AnyHttpUrl(value)).rstrip("/")


class LoggingSettings(BaseModel):
    """Structured logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["console", "json"] = "console"
    redact_keys: list[str] = Field(
        default_factory=lambda: [
            "password",
            "secret",
            "api_key",
            "apikey",
            "authorization",
            "credential",
            "private_key",
            "x-api-key",
        ],
    )


class Settings(BaseSettings):
    """Root settings object.

    Values are read from ``CODEPILOT_*`` environment variables, with nested
    sections using a double underscore (for example
    ``CODEPILOT_DATABASE__URL``). A ``.env`` file in the current directory or
    its parent is loaded when present, which supports running from either
    ``backend/`` or the repository root.
    """

    model_config = SettingsConfigDict(
        env_prefix="CODEPILOT_",
        env_nested_delimiter="__",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "CodePilot AI"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector_db: QdrantSettings = Field(default_factory=QdrantSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @model_validator(mode="after")
    def _validate_production_safety(self) -> Settings:
        """Reject configuration that is unsafe for a production deployment."""
        if self.environment is Environment.PRODUCTION:
            if "*" in self.server.cors_origins:
                raise ValueError("wildcard CORS origins are not allowed in production")
            if self.debug:
                raise ValueError("debug mode must be disabled in production")
        return self
