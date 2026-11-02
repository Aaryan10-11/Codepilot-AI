"""Pure domain models for the tool layer.

Agents in later milestones reference these together with ``models.llm`` when
they decide which tool to call; the models carry no filesystem, subprocess or
I/O behaviour of their own.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ToolName",
    "ToolRisk",
    "ToolResult",
]


class ToolName(StrEnum):
    """Identifiers of every tool agents may request."""

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    TREE = "tree"
    SEARCH_WORKSPACE = "search_workspace"
    GREP = "grep"
    GIT_STATUS = "git_status"
    GIT_DIFF = "git_diff"


class ToolRisk(StrEnum):
    """Side-effect class of a tool.

    ``read_only`` tools never mutate the workspace and run without an
    approval; ``write`` tools change files and always pass the approval gate.
    """

    READ_ONLY = "read_only"
    WRITE = "write"


class ToolResult(BaseModel):
    """Output of one tool invocation.

    Payloads are always text. ``truncated`` marks that output was cut by a
    budget rather than being naturally complete; ``metadata`` carries
    machine-readable facts (line ranges, match counts) without the payload.
    """

    model_config = ConfigDict(frozen=True)

    content: str
    truncated: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolSummary(BaseModel):
    """Describes one registered tool for clients without executing anything."""

    model_config = ConfigDict(frozen=True)

    name: ToolName
    description: str
    risk: ToolRisk
