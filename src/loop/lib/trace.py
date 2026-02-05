"""Trace logging and output utilities.

Provides utilities for logging agent execution traces and displaying
content blocks during agent runs. Used for feedback loop analysis.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from claude_agent_sdk import (
    ContentBlock,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


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
            return BlockInfo("📋", "Result", str(block.content), is_code=True)
        case _:
            return BlockInfo("❓", "Unknown", str(block))


def print_block(block: ContentBlock) -> None:
    """Print a content block to console.

    Args:
        block: A ContentBlock from the Claude Agent SDK.
    """
    info = extract_block_info(block)
    print(f"{info.emoji} {info.content}")


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
