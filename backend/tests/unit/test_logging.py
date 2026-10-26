"""Structured logging configuration and secret redaction."""

from __future__ import annotations

from typing import Any, cast

import pytest
import structlog
from pydantic import SecretStr
from structlog.typing import EventDict

from codepilot.config.logging import (
    REDACTED,
    configure_logging,
    get_logger,
    make_redaction_processor,
)
from codepilot.config.settings import LoggingSettings


def _redact(event: EventDict) -> EventDict:
    processor = make_redaction_processor(LoggingSettings().redact_keys)
    return cast(EventDict, processor(None, "info", event))


def test_sensitive_keys_are_redacted_at_every_depth() -> None:
    event: EventDict = {
        "event": "provider_call",
        "password": "hunter2",
        "nested": {"api_key": "sk-live", "model": "gpt"},
        "items": [{"authorization": "Bearer abc", "count": 1}],
    }

    result = _redact(event)

    assert result["password"] == REDACTED
    nested = result["nested"]
    assert isinstance(nested, dict)
    assert nested["api_key"] == REDACTED
    assert nested["model"] == "gpt"
    items = result["items"]
    assert isinstance(items, list)
    assert items[0]["authorization"] == REDACTED
    assert items[0]["count"] == 1
    assert event["password"] == "hunter2"


def test_token_keys_are_redacted_without_hiding_usage_metrics() -> None:
    result = _redact(
        {
            "event": "llm_call",
            "token": "abc",
            "access_token": "def",
            "token_count": 42,
            "max_tokens": 4096,
        },
    )

    assert result["token"] == REDACTED
    assert result["access_token"] == REDACTED
    assert result["token_count"] == 42
    assert result["max_tokens"] == 4096


def test_secret_str_values_are_always_redacted() -> None:
    result = _redact({"event": "config", "value": SecretStr("do-not-leak")})
    assert result["value"] == REDACTED


def test_json_logging_renders_redacted_event(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LoggingSettings(level="INFO", format="json"))
    logger = get_logger("test.json")

    logger.info("provider_call", api_key="sk-secret", model="gpt")

    output = capsys.readouterr().out
    assert '"event": "provider_call"' in output
    assert "sk-secret" not in output
    assert f'"api_key": "{REDACTED}"' in output


def test_level_filtering_suppresses_debug(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LoggingSettings(level="INFO", format="json"))
    logger = get_logger("test.filtering")

    logger.debug("should_not_appear")

    assert capsys.readouterr().out == ""


def test_console_renderer_produces_readable_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(LoggingSettings(level="INFO", format="console"))
    logger = get_logger("test.console")

    logger.info("started", component="api")

    output = capsys.readouterr().out
    assert "started" in output
    assert "component" in output


def test_context_variables_are_merged(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(LoggingSettings(level="INFO", format="json"))
    logger = get_logger("test.context")

    with structlog.contextvars.bound_contextvars(request_id="req-123"):
        logger.info("handled")

    output: str = capsys.readouterr().out
    assert '"request_id": "req-123"' in output


def test_redaction_leaves_unknown_types_untouched() -> None:
    marker: Any = object()
    result = _redact({"event": "x", "payload": marker})
    assert result["payload"] is marker
