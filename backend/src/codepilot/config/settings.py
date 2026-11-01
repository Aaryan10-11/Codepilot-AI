"""Typed, environment-driven application configuration.

All configuration is expressed as nested pydantic models so that wiring code
receives small, validated objects instead of reading ``os.environ`` directly.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from codepilot.models.llm import ProviderId


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


# Canonical models used when a provider block does not name one explicitly.
# These are configuration defaults, not capabilities; override per environment.
_CANONICAL_DEFAULT_MODELS: dict[ProviderId, str] = {
    ProviderId.OPENAI: "gpt-4.1",
    ProviderId.ANTHROPIC: "claude-sonnet-4-5",
    ProviderId.GOOGLE: "gemini-2.5-flash",
    ProviderId.DEEPSEEK: "deepseek-chat",
}


class ProviderSettings(BaseModel):
    """Connection settings for exactly one LLM provider.

    ``api_key`` accepts ``CODEPILOT_LLM__<PROVIDER>__API_KEY`` and, as a
    convenience, the provider's own documented variable (``OPENAI_API_KEY``,
    ``ANTHROPIC_API_KEY``, ``GEMINI_API_KEY``/``GOOGLE_API_KEY``,
    ``DEEPSEEK_API_KEY``) — see ``codepilot.llm.credentials``.
    """

    api_key: SecretStr | None = None
    base_url: str | None = None
    timeout_seconds: float = Field(default=180.0, gt=0, le=600)
    default_model: str | None = None


class RetrySettings(BaseModel):
    """Retry policy applied to failed provider calls."""

    max_attempts: int = Field(default=3, ge=1, le=8)
    base_delay_seconds: float = Field(default=0.5, gt=0, le=30)
    max_delay_seconds: float = Field(default=8.0, gt=0, le=120)
    jitter: float = Field(default=0.1, ge=0, le=1)


class LLMSettings(BaseModel):
    """Model provider configuration.

    Every provider block is independent; a missing API key simply makes that
    provider unavailable rather than failing the process. Provided provider
    blocks are re-validated so callers can never bypass field constraints.
    """

    model_config = ConfigDict(revalidate_instances="always")

    default_provider: ProviderId = ProviderId.OPENAI
    openai: ProviderSettings = Field(default_factory=ProviderSettings)
    anthropic: ProviderSettings = Field(default_factory=ProviderSettings)
    google: ProviderSettings = Field(default_factory=ProviderSettings)
    deepseek: ProviderSettings = Field(default_factory=ProviderSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)

    @field_validator("openai", "anthropic", "google", "deepseek", mode="before")
    @classmethod
    def _revalidate_provider_block(cls, value: object) -> object:
        """Re-validate provided provider blocks; model_copy bypasses field checks."""
        if isinstance(value, ProviderSettings):
            return ProviderSettings.model_validate(value.model_dump())
        return value

    def model_for(self, provider_id: ProviderId) -> str:
        """Return the configured default model for one provider."""
        section = self._section(provider_id)
        if section.default_model is None:  # pragma: no cover - validator fills it
            raise ValueError(f"default model for {provider_id.value} is not resolved")
        return section.default_model

    def section(self, provider_id: ProviderId) -> ProviderSettings:
        """Return the settings block for one provider."""
        return self._section(provider_id)

    @model_validator(mode="after")
    def _fill_default_models(self) -> LLMSettings:
        """Give every provider a canonical default model when unset."""
        for provider_id in ProviderId:
            section = self._section(provider_id)
            if section.default_model is None:
                section.default_model = _CANONICAL_DEFAULT_MODELS[provider_id]
        return self

    def _section(self, provider_id: ProviderId) -> ProviderSettings:
        return {
            ProviderId.OPENAI: self.openai,
            ProviderId.ANTHROPIC: self.anthropic,
            ProviderId.GOOGLE: self.google,
            ProviderId.DEEPSEEK: self.deepseek,
        }[provider_id]


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
    llm: LLMSettings = Field(default_factory=LLMSettings)
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
