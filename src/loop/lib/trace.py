"""Trace logging and output utilities.

Provides utilities for logging agent execution traces and displaying
content blocks during agent runs. Used for feedback loop analysis.

Content blocks are displayed with color-coded tool use/result pairing
using Rich console, making it easy to visually track which result
belongs to which tool call.
"""

import itertools
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from rich.console import Console

from claude_agent_sdk import (
    ContentBlock,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color-coded tool use / result pairing
# ---------------------------------------------------------------------------

_TOOL_COLORS = [
    "cyan",
    "green",
    "yellow",
    "magenta",
    "blue",
    "red",
    "bright_cyan",
    "bright_green",
    "bright_yellow",
    "bright_magenta",
    "bright_blue",
    "bright_red",
]
_color_cycle = itertools.cycle(_TOOL_COLORS)
_id_to_color: dict[str, str] = {}
_console = Console(highlight=False, markup=False)
stream_log = logging.getLogger("loop.agent.stream")


# ---------------------------------------------------------------------------
# Content normalization
# ---------------------------------------------------------------------------


def normalize_content(content: str | list[Any] | None) -> str:
    """Convert MCP content blocks to a plain string."""
    if content is None:
        return "(empty)"
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(str(item.get("text", "")))
        return "\n".join(texts)
    return str(content)


def truncate_content(content: str | list[Any] | None, max_len: int = 500) -> str:
    """Normalize and truncate content for display."""
    text = normalize_content(content)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


# ---------------------------------------------------------------------------
# Block info extraction
# ---------------------------------------------------------------------------


class BlockInfo(NamedTuple):
    """Extracted information from a content block."""

    emoji: str
    label: str
    content: str
    is_code: bool = False


def extract_block_info(block: ContentBlock) -> BlockInfo:
    """Extract display information from a content block.

    Args:
        block: A ContentBlock from the Claude Agent SDK.

    Returns:
        BlockInfo with emoji, label, and content.
    """
    match block:
        case ThinkingBlock():
            return BlockInfo("💭", "Thinking", block.thinking)
        case TextBlock():
            return BlockInfo("💬", "Response", block.text)
        case ToolUseBlock():
            content = json.dumps(block.input, indent=2) if block.input else ""
            return BlockInfo("🔧", f"Tool: {block.name}", content, is_code=True)
        case ToolResultBlock():
            return BlockInfo("📋", "Result", normalize_content(block.content), is_code=True)
        case _:
            return BlockInfo("❓", "Unknown", str(block))


# ---------------------------------------------------------------------------
# Console display
# ---------------------------------------------------------------------------


def print_block(block: ContentBlock, prefix: str = "") -> None:
    """Print a content block with color-coded tool use/result pairing.

    ToolUseBlock and ToolResultBlock are linked by color: when a tool use
    is printed, its ID is assigned a color from a rotating palette. When
    the corresponding result arrives, the same color is used, making it
    easy to visually pair them.

    Args:
        block: A ContentBlock from the Claude Agent SDK.
        prefix: Optional prefix for visual nesting.
    """
    match block:
        case ThinkingBlock():
            print(f"{prefix}💭 {block.thinking}")
            stream_log.info("%sTHINKING: %s", prefix, block.thinking)
        case TextBlock():
            print(f"{prefix}💬 {block.text}")
            stream_log.info("%sTEXT: %s", prefix, block.text)
        case ToolUseBlock():
            color = next(_color_cycle)
            _id_to_color[block.id] = color
            print(f"{prefix}🔧 {block.name} ", end="")
            _console.print(f"[{block.id}]", style=color)
            if block.input:
                print(json.dumps(block.input, indent=2))
            stream_log.info(
                "%sTOOL_USE [%s] %s: %s",
                prefix,
                block.id,
                block.name,
                json.dumps(block.input) if block.input else "",
            )
        case ToolResultBlock():
            color = _id_to_color.pop(block.tool_use_id, "default")
            print(f"{prefix}📋 Result ", end="")
            _console.print(f"[{block.tool_use_id}]", style=color, end="")
            print(": ", end="")
            print(truncate_content(block.content, max_len=500))
            stream_log.info(
                "%sTOOL_RESULT [%s]: %s",
                prefix,
                block.tool_use_id,
                normalize_content(block.content),
            )
        case _:
            print(f"{prefix}❓ {type(block).__name__}: {block}")
            stream_log.info("%sUNKNOWN: %s: %s", prefix, type(block).__name__, block)


# ---------------------------------------------------------------------------
# Markdown formatting for traces
# ---------------------------------------------------------------------------


def format_block_markdown(block: ContentBlock) -> str:
    """Format a content block as markdown for trace logs.

    Args:
        block: A ContentBlock from the Claude Agent SDK.

    Returns:
        Markdown-formatted string representation.
    """
    info = extract_block_info(block)
    if info.is_code:
        lang = "json" if "Tool:" in info.label else ""
        return f"## {info.emoji} {info.label}\n\n```{lang}\n{info.content}\n```\n"
    return f"## {info.emoji} {info.label}\n\n{info.content}\n"


# ---------------------------------------------------------------------------
# Trace logger
# ---------------------------------------------------------------------------


class TraceLogger(BaseModel):
    """Accumulates agent reasoning for feedback loop analysis.

    Collects content blocks during agent execution and saves them
    as a markdown trace file for later analysis.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    trace_path: Path = Field(description="Path to save the trace file")
    title: str = Field(description="Title for the trace")
    lines: list[str] = Field(default_factory=list)

    def model_post_init(self, _context: Any) -> None:
        """Initialize the trace with header."""
        if not self.lines:
            self.lines.append(f"# Trace: {self.title}\n")
            self.lines.append(f"*Generated: {datetime.now().isoformat()}*\n\n")

    def log_block(self, block: ContentBlock) -> None:
        """Add a formatted block to the trace.

        Args:
            block: A ContentBlock from the Claude Agent SDK.
        """
        self.lines.append(format_block_markdown(block))

    def log_text(self, text: str, heading: str | None = None) -> None:
        """Add raw text to the trace.

        Args:
            text: Text content to add.
            heading: Optional heading for the section.
        """
        if heading:
            self.lines.append(f"## {heading}\n\n{text}\n")
        else:
            self.lines.append(f"{text}\n")

    def save(self) -> Path:
        """Write accumulated trace to file.

        Returns:
            Path to the saved trace file.
        """
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_path.write_text("\n".join(self.lines), encoding="utf-8")
        logger.info("Saved trace to %s", self.trace_path)
        return self.trace_path
