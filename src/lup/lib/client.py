"""Centralized Agent SDK client creation and response collection.

All Agent SDK client construction goes through this module to ensure
consistent defaults (session persistence disabled for sub-agent calls).

Exports:
- ResponseCollector — reusable "iterate, print, log, collect" pattern
- build_client() — AsyncContextManager[ClaudeSDKClient] with defaults
- run_query(prompt, ...) — query + collect in one call, returns ResponseCollector
- one_shot(prompt, ...) — prompt->result convenience for tool-free LLM calls
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, overload

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ContentBlock, Message
from claude_agent_sdk.types import (
    AgentDefinition,
    AssistantMessage,
    HookEvent,
    HookMatcher,
    McpServerConfig,
    ResultMessage,
    SystemMessage,
    SystemPromptPreset,
    ToolsPreset,
    UserMessage,
)
from pydantic import BaseModel

from lup.lib.trace import TraceLogger, print_message

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output format types
# ---------------------------------------------------------------------------

JsonSchema = dict[str, object]
"""Type alias for JSON Schema payloads (from ``BaseModel.model_json_schema()``)."""

OutputFormat = dict[str, str | JsonSchema]
"""SDK output format dict (e.g. ``{"type": "json_schema", "schema": ...}``)."""


# ---------------------------------------------------------------------------
# Response collector
# ---------------------------------------------------------------------------


class ResponseCollector:
    """Collects, displays, and logs agent response messages.

    Supports two usage patterns:

    **async for** — iterate messages yourself, no automatic display::

        collector = ResponseCollector(client, trace_logger=trace_logger)
        async for message in collector:
            print_message(message)

    **collect()** — drain all messages with automatic display::

        collector = ResponseCollector(client, trace_logger=trace_logger)
        result = await collector.collect()

    After iteration, access accumulated state:
    ``collector.blocks``, ``collector.tool_results``,
    ``collector.messages``, ``collector.result``.
    """

    def __init__(
        self,
        client: ClaudeSDKClient,
        trace_logger: TraceLogger | None = None,
        prefix: str = "",
    ) -> None:
        self.client = client
        self.blocks: list[ContentBlock] = []
        self.tool_results: list[ContentBlock] = []
        self.messages: list[AssistantMessage | UserMessage] = []
        self.result: ResultMessage | None = None
        self.trace_logger = trace_logger
        self.prefix = prefix

    async def __aiter__(self) -> AsyncIterator[Message]:
        """Yield messages, accumulating state but not displaying.

        Raises RuntimeError on agent error results.
        """
        async for message in self.client.receive_response():
            match message:
                case AssistantMessage():
                    self.messages.append(message)
                    for block in message.content:
                        self.blocks.append(block)

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
                            self.tool_results.append(block)

            yield message

    async def collect(self) -> ResultMessage:
        """Drain all messages, displaying blocks, and return the result.

        Shorthand for ``async for`` with ``print_message`` on every message.

        Raises:
            RuntimeError: If the agent returns an error or no result.
        """
        async for message in self:
            print_message(message, prefix=self.prefix, trace_logger=self.trace_logger)

        if self.result is None:
            raise RuntimeError("No result received from agent")
        return self.result


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------


@asynccontextmanager
async def build_client(
    *,
    options: ClaudeAgentOptions | None = None,
    model: str | None = None,
    system_prompt: str | SystemPromptPreset | None = None,
    tools: list[str] | ToolsPreset | None = None,
    allowed_tools: list[str] | None = None,
    permission_mode: Literal["default", "acceptEdits", "plan", "bypassPermissions"] | None = None,
    mcp_servers: dict[str, McpServerConfig] | str | Path | None = None,
    agents: dict[str, AgentDefinition] | None = None,
    max_thinking_tokens: int | None = None,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
    output_format: OutputFormat | None = None,
    extra_args: dict[str, str | None] | None = None,
    hooks: dict[HookEvent, list[HookMatcher]] | None = None,
) -> AsyncIterator[ClaudeSDKClient]:
    """Return a configured ClaudeSDKClient with project-wide defaults.

    Pass ``options`` (pre-built) to use as-is, or keyword arguments to
    construct ClaudeAgentOptions.  When using keyword arguments, always
    injects ``no-session-persistence`` into extra_args (caller wins on
    conflict).
    """
    if options is None:
        merged_extra: dict[str, str | None] = {
            "no-session-persistence": None,
            **(extra_args or {}),
        }
        options = ClaudeAgentOptions(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            allowed_tools=allowed_tools if allowed_tools is not None else [],
            permission_mode=permission_mode,
            mcp_servers=mcp_servers if mcp_servers is not None else {},
            agents=agents,
            max_thinking_tokens=max_thinking_tokens,
            max_turns=max_turns,
            max_budget_usd=max_budget_usd,
            output_format=output_format,
            extra_args=merged_extra,
            hooks=hooks,
        )

    async with ClaudeSDKClient(options=options) as client:
        yield client


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


async def run_query(
    prompt: str,
    *,
    options: ClaudeAgentOptions | None = None,
    prefix: str = "",
    trace_logger: TraceLogger | None = None,
    model: str | None = None,
    system_prompt: str | SystemPromptPreset | None = None,
    tools: list[str] | ToolsPreset | None = None,
    allowed_tools: list[str] | None = None,
    permission_mode: Literal["default", "acceptEdits", "plan", "bypassPermissions"] | None = None,
    mcp_servers: dict[str, McpServerConfig] | str | Path | None = None,
    agents: dict[str, AgentDefinition] | None = None,
    max_thinking_tokens: int | None = None,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
    output_format: OutputFormat | None = None,
    extra_args: dict[str, str | None] | None = None,
    hooks: dict[HookEvent, list[HookMatcher]] | None = None,
) -> ResponseCollector:
    """Query an SDK client and collect the full response.

    Combines build_client + query + ResponseCollector.collect into a
    single call.  Pass either ``options`` or keyword arguments for
    ClaudeAgentOptions.

    Returns the ResponseCollector with .result, .blocks, .messages.
    """
    async with build_client(
        options=options,
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        allowed_tools=allowed_tools,
        permission_mode=permission_mode,
        mcp_servers=mcp_servers,
        agents=agents,
        max_thinking_tokens=max_thinking_tokens,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        output_format=output_format,
        extra_args=extra_args,
        hooks=hooks,
    ) as client:
        await client.query(prompt)
        collector = ResponseCollector(client, prefix=prefix, trace_logger=trace_logger)
        await collector.collect()
    return collector


@overload
async def one_shot(
    prompt: str,
    *,
    model: str = ...,
    system_prompt: str = ...,
    prefix: str = ...,
) -> str | None: ...


@overload
async def one_shot[T: BaseModel](
    prompt: str,
    *,
    model: str = ...,
    system_prompt: str = ...,
    output_type: type[T],
    prefix: str = ...,
) -> T | None: ...


async def one_shot(
    prompt: str,
    *,
    model: str = "sonnet",
    system_prompt: str = "",
    output_type: type[BaseModel] | None = None,
    prefix: str = "",
) -> BaseModel | str | None:
    """One-shot prompt->result convenience wrapper.

    Without output_type: returns the text result (str).
    With output_type: returns a validated Pydantic model from structured output.
    """
    output_format: OutputFormat | None = None
    if output_type is not None:
        output_format = {
            "type": "json_schema",
            "schema": output_type.model_json_schema(),
        }

    collector = await run_query(
        prompt,
        prefix=prefix,
        model=model,
        system_prompt=system_prompt,
        allowed_tools=[],
        output_format=output_format,
    )

    if collector.result is None:
        return None
    if output_type is not None and collector.result.structured_output:
        return output_type.model_validate(collector.result.structured_output)
    if output_type is not None:
        return None
    return collector.result.result
