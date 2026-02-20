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
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from rich.console import Console

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ContentBlock,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
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
stream_log = logging.getLogger("lup.agent.stream")


# ---------------------------------------------------------------------------
# Content normalization
# ---------------------------------------------------------------------------


def normalize_content(content: str | Sequence[object] | None) -> str:
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


def _truncate_str(value: str, max_len: int = 500) -> str:
    if len(value) > max_len:
        return value[:max_len] + "..."
    return value


def _truncate_str_fields(obj: object, max_len: int = 500) -> object:
    """Recursively truncate string values in a JSON-like structure."""
    if isinstance(obj, dict):
        return {k: _truncate_str_fields(v, max_len) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate_str_fields(item, max_len) for item in obj]
    if isinstance(obj, str):
        return _truncate_str(obj, max_len)
    return obj


def format_tool_result(
    content: str | Sequence[object] | None, max_len: int = 500
) -> str:
    """Format tool result content for display.

    If the content parses as a JSON dict, pretty-print it with string fields
    truncated. Otherwise fall back to plain truncation.
    """
    text = normalize_content(content)
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return _truncate_str(text, max_len)
    truncated = _truncate_str_fields(parsed, max_len)
    return json.dumps(truncated, indent=2)


def truncate_content(content: str | Sequence[object] | None, max_len: int = 500) -> str:
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
            return BlockInfo(
                "📋", "Result", normalize_content(block.content), is_code=True
            )
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
            formatted = format_tool_result(block.content)
            print(f"{prefix}📋 Result ", end="")
            _console.print(f"[{block.tool_use_id}]", style=color)
            print(formatted)
            stream_log.info(
                "%sTOOL_RESULT [%s]: %s",
                prefix,
                block.tool_use_id,
                formatted,
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


class TraceEntry(BaseModel):
    """A single indexed entry in a session trace."""

    index: int = Field(description="0-based entry index")
    timestamp: str = Field(description="ISO timestamp when entry was logged")
    content: str = Field(description="Markdown content for this entry")


class TraceLogger(BaseModel):
    """Accumulates agent reasoning for feedback loop analysis.

    Collects content blocks during agent execution and saves them
    as a markdown trace file for later analysis. Supports both
    raw line access (for saving) and indexed entry access (for slicing).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    trace_path: Path = Field(description="Path to save the trace file")
    title: str = Field(description="Title for the trace")
    lines: list[str] = Field(default_factory=list)
    entries: list[TraceEntry] = Field(default_factory=list)

    def model_post_init(self, _context: object) -> None:
        """Initialize the trace with header."""
        if not self.lines:
            header = f"# Trace: {self.title}\n"
            generated = f"*Generated: {datetime.now().isoformat()}*\n\n"
            self.lines.append(header)
            self.lines.append(generated)
            self.entries.append(
                TraceEntry(
                    index=0,
                    timestamp=datetime.now().isoformat(),
                    content=header + generated,
                )
            )

    def _append_entry(self, content: str) -> None:
        """Create and append a new trace entry."""
        self.lines.append(content)
        self.entries.append(
            TraceEntry(
                index=len(self.entries),
                timestamp=datetime.now().isoformat(),
                content=content,
            )
        )

    def log_block(self, block: ContentBlock) -> None:
        """Add a formatted block to the trace."""
        self._append_entry(format_block_markdown(block))

    def log_text(self, text: str, heading: str | None = None) -> None:
        """Add raw text to the trace."""
        if heading:
            self._append_entry(f"## {heading}\n\n{text}\n")
        else:
            self._append_entry(f"{text}\n")

    def read_entries(
        self,
        after_n: int | None = None,
        before_n: int | None = None,
    ) -> list[TraceEntry]:
        """Slice entries by index. Supports negative indexing."""
        return self.entries[after_n:before_n]

    def save(self) -> Path:
        """Write accumulated trace to file."""
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_path.write_text("\n".join(self.lines), encoding="utf-8")
        logger.info("Saved trace to %s", self.trace_path)
        return self.trace_path


# ---------------------------------------------------------------------------
# Response collector — reusable "call SDK, iterate blocks, print+log" pattern
# ---------------------------------------------------------------------------


class ResponseCollector:
    """Collects, displays, and logs agent response messages.

    Encapsulates the common pattern of iterating over SDK response messages,
    printing and logging each content block, and collecting text and messages
    for post-processing.

    Usage::

        collector = ResponseCollector(trace_logger=trace_logger)
        result = await collector.collect(client)
        # Access collector.assistant_messages, collector.collected_text, etc.
    """

    def __init__(
        self,
        trace_logger: TraceLogger | None = None,
        prefix: str = "",
    ) -> None:
        self.blocks: list[ContentBlock] = []
        self.messages: list[AssistantMessage | UserMessage] = []
        self.result: ResultMessage | None = None
        self._trace_logger = trace_logger
        self._prefix = prefix

    def _handle_block(self, block: ContentBlock) -> None:
        """Print, log, and collect a single content block."""
        self.blocks.append(block)
        print_block(block, prefix=self._prefix)
        if self._trace_logger:
            self._trace_logger.log_block(block)

    async def collect(self, client: ClaudeSDKClient) -> ResultMessage:
        """Iterate response, print+log blocks, and return the result.

        Raises:
            RuntimeError: If the agent returns an error or no result.
        """
        async for message in client.receive_response():
            match message:
                case AssistantMessage():
                    self.messages.append(message)
                    for block in message.content:
                        self._handle_block(block)

                case ResultMessage():
                    self.result = message
                    if message.is_error:
                        raise RuntimeError(f"Agent error: {message.result}")

                case SystemMessage():
                    logger.info("System [%s]: %s", message.subtype, message.data)

                case UserMessage():
                    self.messages.append(message)
                    if isinstance(message.content, list):
                        for block in message.content:
                            self._handle_block(block)

        if self.result is None:
            raise RuntimeError("No result received from agent")
        return self.result
