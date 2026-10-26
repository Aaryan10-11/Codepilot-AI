"""Structured logging setup with context propagation and secret redaction."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable, Mapping
from typing import Any, cast

import structlog
from pydantic import SecretStr
from structlog.typing import EventDict, Processor

from codepilot.config.settings import LoggingSettings

REDACTED = "***"


def _is_sensitive_key(key: str, markers: tuple[str, ...]) -> bool:
    lowered = key.lower()
    if lowered == "token" or lowered.endswith("_token"):
        return True
    return any(marker in lowered for marker in markers)


def _redact(value: object, markers: tuple[str, ...]) -> object:
    if isinstance(value, SecretStr):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_sensitive_key(str(key), markers) else _redact(item, markers)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item, markers) for item in value]
    return value


def make_redaction_processor(markers: Iterable[str]) -> Processor:
    """Build a structlog processor that masks sensitive keys at any depth."""
    normalised = tuple(marker.lower() for marker in markers)

    def processor(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
        return cast(EventDict, _redact(event_dict, normalised))

    return processor


def configure_logging(settings: LoggingSettings) -> None:
    """Configure structlog for the current process.

    Called once during application startup. ``PrintLogger`` writes to stdout so
    that container log collection works without stdlib handler plumbing.
    """
    level = logging.getLevelNamesMapping()[settings.level]
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        make_redaction_processor(settings.redact_keys),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.format == "json":
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger; safe to call before configuration for tests."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
