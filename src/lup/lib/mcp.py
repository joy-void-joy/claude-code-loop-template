"""Patched MCP server factory that preserves is_error from tool responses.

The Claude Agent SDK's `create_sdk_mcp_server` has bugs that prevent proper error
propagation:

1. It discards `is_error` from dict responses, only extracting `content`
2. Its query.py checks `is_error` (snake_case) but MCP's CallToolResult uses
   `isError` (camelCase)

This module provides a fixed version that works around both issues.

Use `create_mcp_server` instead of `create_sdk_mcp_server` from claude_agent_sdk.

SDK Compatibility
-----------------
Tested against: claude-agent-sdk>=0.1.26
Last verified: 2026-02-04

Maintenance Notes:
- Check if these bugs are fixed in future SDK versions
- If fixed, remove the patched code and alias `create_mcp_server = create_sdk_mcp_server`
- Update pyproject.toml to require the fixed version minimum
- Monitor SDK changelog for MCP-related changes

Tool naming convention:
    After registration, tools are named: mcp__{server_name}__{tool_name}
    Example: mcp__my-server__my_tool
"""

import inspect
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypedDict, cast, get_type_hints

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig
from mcp.server import Server
from mcp.types import CallToolResult, ContentBlock, ImageContent, TextContent, Tool
from pydantic import BaseModel, TypeAdapter, ValidationError

logger = logging.getLogger(__name__)


class ToolResponse(TypedDict, total=False):
    """Shape of the dict returned by MCP tool handlers."""

    content: list[dict[str, str]]
    is_error: bool


def generate_json_schema(
    input_schema: type | dict[str, type | str],
) -> dict[str, object]:
    """Generate JSON Schema from input_schema (TypedDict, BaseModel, or dict).

    Args:
        input_schema: Either a dict (simple type mapping or full schema),
                      a TypedDict class, or a Pydantic BaseModel class.

    Returns:
        A valid JSON Schema dict for MCP tool registration.
    """
    if isinstance(input_schema, dict):
        if "type" in input_schema and "properties" in input_schema:
            return cast(dict[str, object], input_schema)
        type_map: dict[type, str] = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
        }
        properties: dict[str, dict[str, str]] = {}
        for param_name, param_type in input_schema.items():
            if isinstance(param_type, type):
                properties[param_name] = {"type": type_map.get(param_type, "string")}
            else:
                properties[param_name] = {"type": str(param_type)}
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        }

    try:
        adapter = TypeAdapter(input_schema)
        return cast(dict[str, object], adapter.json_schema())
    except TypeError as e:
        logger.warning(
            "TypeAdapter doesn't support %s: %s. Using empty schema.",
            input_schema,
            e,
        )
        return {"type": "object", "properties": {}}


class CallToolResultWithAlias(CallToolResult):
    """CallToolResult with snake_case alias for SDK compatibility.

    The Claude Agent SDK's query.py checks `is_error` (snake_case) but MCP's
    CallToolResult uses `isError` (camelCase). This subclass adds a property
    alias so both work.
    """

    @property
    def is_error(self) -> bool:
        """Snake_case alias for isError (SDK compatibility)."""
        return self.isError


def create_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: Sequence[SdkMcpTool[Any]] | None = None,
) -> McpSdkServerConfig:
    """Create an in-process MCP server with proper is_error handling.

    This is a patched version of claude_agent_sdk.create_sdk_mcp_server that
    properly preserves the `is_error` flag from tool responses.

    Args:
        name: Unique identifier for the server.
        version: Server version string.
        tools: List of SdkMcpTool instances created with the @tool decorator.

    Returns:
        McpSdkServerConfig for use with ClaudeAgentOptions.mcp_servers.
    """
    server = Server(name, version=version)
    server._tools = tools or []  # type: ignore[attr-defined]

    if tools:
        tool_map = {tool_def.name: tool_def for tool_def in tools}

        @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
        async def list_tools() -> list[Tool]:
            """Return the list of available tools."""
            tool_list: list[Tool] = []
            for tool_def in tools:
                schema = generate_json_schema(tool_def.input_schema)
                tool_list.append(
                    Tool(
                        name=tool_def.name,
                        description=tool_def.description,
                        inputSchema=schema,
                    )
                )
            return tool_list

        @server.call_tool()  # type: ignore[untyped-decorator]
        async def call_tool(name: str, arguments: dict[str, object]) -> CallToolResult:
            """Execute a tool by name with given arguments."""
            if name not in tool_map:
                raise ValueError(f"Tool '{name}' not found")

            tool_def = tool_map[name]
            result = cast(ToolResponse, await tool_def.handler(arguments))

            is_error = result.get("is_error", False)

            content: list[TextContent | ImageContent] = []
            if "content" in result:
                for item in result["content"]:
                    match item.get("type"):
                        case "text":
                            content.append(TextContent(type="text", text=item["text"]))
                        case "image":
                            content.append(
                                ImageContent(
                                    type="image",
                                    data=item["data"],
                                    mimeType=item["mimeType"],
                                )
                            )

            return CallToolResultWithAlias(
                content=cast(list[ContentBlock], content), isError=is_error
            )

    return McpSdkServerConfig(type="sdk", name=name, instance=server)


class ToolError(Exception):
    """Raise in a tool handler to return an MCP error response."""


class LupMcpTool:
    """MCP tool with typed input/output models for introspection.

    Wraps ``SdkMcpTool`` and preserves the original BaseModel classes so that
    devtools (``lup-devtools agent inspect``) can display full JSON Schemas
    for both input and output.
    """

    def __init__(
        self,
        sdk_tool: SdkMcpTool[Any],
        input_model: type[BaseModel],
        output_model: type[BaseModel] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.sdk_tool = sdk_tool
        self.input_model = input_model
        self.output_model = output_model
        self.tags = tags or []


def lup_tool(
    description: str,
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    *,
    name: str | None = None,
    tags: list[str] | None = None,
) -> Callable[
    [Callable[..., Awaitable[BaseModel]]],
    LupMcpTool,
]:
    """Decorator for defining MCP tools with typed input/output models.

    Like the SDK's ``@tool`` but infers input/output schemas from type
    annotations, auto-validates input, auto-serializes BaseModel output,
    and tracks call metrics (duration, errors).

    The handler receives a validated model instance, not a raw dict.
    The handler must return a BaseModel, which is auto-serialized via
    ``mcp_success(result.model_dump())``.

    Raise ``ToolError`` in the handler to return an MCP error response.

    Args:
        description: What/when/why — the agent's only documentation for this tool.
        input_model: Pydantic BaseModel for the tool's input.
              Inferred from the handler's first parameter type if omitted.
        output_model: Pydantic BaseModel for the tool's output.
              Inferred from the handler's return type if omitted.
        name: Unique tool identifier (becomes ``mcp__{server}__{name}``).
              Defaults to the handler's function name.
        tags: Optional classification tags for tool policy filtering.

    Returns:
        A decorator that wraps the async handler into a ``LupMcpTool``.
    """
    from lup.lib.metrics import collector
    from lup.lib.responses import mcp_error, mcp_success

    def decorator(
        handler: Callable[..., Awaitable[BaseModel]],
    ) -> LupMcpTool:
        tool_name = name or handler.__name__

        resolved_input = input_model
        resolved_output = output_model

        if resolved_input is None or resolved_output is None:
            hints = get_type_hints(handler)
            if resolved_input is None:
                params = list(inspect.signature(handler).parameters.values())
                if not params:
                    msg = f"lup_tool '{tool_name}': handler has no parameters to infer input_model from"
                    raise TypeError(msg)
                param_type = hints.get(params[0].name)
                if isinstance(param_type, type) and issubclass(param_type, BaseModel):
                    resolved_input = param_type
            if resolved_output is None:
                return_type = hints.get("return")
                if isinstance(return_type, type) and issubclass(return_type, BaseModel):
                    resolved_output = return_type

        if resolved_input is None:
            msg = f"lup_tool '{tool_name}': cannot infer input_model from annotations"
            raise TypeError(msg)

        final_input: type[BaseModel] = resolved_input

        async def wrapper(args: dict[str, Any]) -> dict[str, Any]:
            start = time.perf_counter()
            is_error = False
            try:
                try:
                    params = final_input.model_validate(args)
                except ValidationError as e:
                    is_error = True
                    return mcp_error(f"Invalid input: {e}")
                try:
                    result = await handler(params)
                except ToolError as e:
                    is_error = True
                    return mcp_error(str(e))
                if not isinstance(result, BaseModel):
                    raise TypeError(
                        f"lup_tool '{tool_name}': handler must return a BaseModel, "
                        f"got {type(result).__name__}"
                    )
                if resolved_output is not None and not isinstance(result, resolved_output):
                    raise TypeError(
                        f"lup_tool '{tool_name}': expected {resolved_output.__name__}, "
                        f"got {type(result).__name__}"
                    )
                return mcp_success(result.model_dump())
            except Exception:
                is_error = True
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                collector.record(tool_name, duration_ms, is_error)

        sdk = SdkMcpTool(
            name=tool_name,
            description=description,
            input_schema=final_input.model_json_schema(),
            handler=cast(Callable[[Any], Awaitable[dict[str, Any]]], wrapper),
        )
        return LupMcpTool(
            sdk_tool=sdk,
            input_model=final_input,
            output_model=resolved_output,
            tags=tags,
        )

    return decorator


def extract_sdk_tools(tools: list[LupMcpTool]) -> list[SdkMcpTool[Any]]:
    """Extract SdkMcpTool instances from a list of LupMcpTools.

    Use this when passing tools to ``create_mcp_server`` or
    ``create_sdk_mcp_server``, which expect ``list[SdkMcpTool]``.
    """
    return [t.sdk_tool for t in tools]


__all__ = [
    "LupMcpTool",
    "ToolError",
    "create_mcp_server",
    "create_sdk_mcp_server",
    "extract_sdk_tools",
    "lup_tool",
    "tool",
]
