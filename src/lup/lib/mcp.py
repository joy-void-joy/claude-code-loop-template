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

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict, cast

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig
from mcp.server import Server
from mcp.types import CallToolResult, ContentBlock, ImageContent, TextContent, Tool
from pydantic import BaseModel, TypeAdapter

logger = logging.getLogger(__name__)


def _generate_json_schema(input_schema: type | dict[str, Any]) -> dict[str, Any]:
    """Generate JSON Schema from input_schema (TypedDict, BaseModel, or dict).

    Args:
        input_schema: Either a dict (simple type mapping or full schema),
                      a TypedDict class, or a Pydantic BaseModel class.

    Returns:
        A valid JSON Schema dict for MCP tool registration.
    """
    if isinstance(input_schema, dict):
        # Already a full JSON schema
        if "type" in input_schema and "properties" in input_schema:
            return input_schema
        # Simple type mapping dict like {"post_id": int, "query": str}
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
        }
        properties = {}
        for param_name, param_type in input_schema.items():
            properties[param_name] = {"type": type_map.get(param_type, "string")}
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        }

    # TypedDict or Pydantic BaseModel - use TypeAdapter for schema generation
    try:
        adapter = TypeAdapter(input_schema)
        return adapter.json_schema()
    except TypeError as e:
        logger.warning(
            "TypeAdapter doesn't support %s: %s. Using empty schema.",
            input_schema,
            e,
        )
        return {"type": "object", "properties": {}}


class _CallToolResultWithAlias(CallToolResult):
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
    name: str, version: str = "1.0.0", tools: list[SdkMcpTool[Any]] | None = None
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
            tool_list = []
            for tool_def in tools:
                schema = _generate_json_schema(tool_def.input_schema)
                tool_list.append(
                    Tool(
                        name=tool_def.name,
                        description=tool_def.description,
                        inputSchema=schema,
                    )
                )
            return tool_list

        @server.call_tool()  # type: ignore[untyped-decorator]
        async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
            """Execute a tool by name with given arguments."""
            if name not in tool_map:
                raise ValueError(f"Tool '{name}' not found")

            tool_def = tool_map[name]
            result = await tool_def.handler(arguments)

            # Extract is_error flag (FIX: SDK's wrapper discards this)
            is_error = result.get("is_error", False)

            # Convert content to MCP types
            content: list[TextContent | ImageContent] = []
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        content.append(TextContent(type="text", text=item["text"]))
                    if item.get("type") == "image":
                        content.append(
                            ImageContent(
                                type="image",
                                data=item["data"],
                                mimeType=item["mimeType"],
                            )
                        )

            return _CallToolResultWithAlias(
                content=cast(list[ContentBlock], content), isError=is_error
            )

    return McpSdkServerConfig(type="sdk", name=name, instance=server)


class _LupMcpToolRequired(TypedDict):
    """Required fields for LupMcpTool."""

    sdk_tool: SdkMcpTool[Any]
    input_model: type[BaseModel]


class LupMcpTool(_LupMcpToolRequired, total=False):
    """MCP tool with typed input/output models for introspection.

    Wraps ``SdkMcpTool`` and preserves the original BaseModel classes so that
    devtools (``lup-devtools agent inspect``) can display full JSON Schemas
    for both input and output.
    """

    output_model: type[BaseModel]
    tags: list[str]


def lup_tool(
    name: str,
    description: str,
    input_model: type[BaseModel],
    output_model: type[BaseModel] | None = None,
) -> Callable[
    [Callable[[Any], Awaitable[dict[str, Any]]]],
    LupMcpTool,
]:
    """Decorator for defining MCP tools with typed input/output models.

    Like the SDK's ``@tool`` but accepts BaseModel classes directly and
    stores them for introspection. The input schema is generated via
    ``model_json_schema()`` automatically.

    Args:
        name: Unique tool identifier (becomes ``mcp__{server}__{name}``).
        description: What/when/why — the agent's only documentation for this tool.
        input_model: Pydantic BaseModel class defining the tool's input.
        output_model: Optional Pydantic BaseModel class defining the tool's output.

    Returns:
        A decorator that wraps the async handler into a ``LupMcpTool``.
    """

    def decorator(
        handler: Callable[[Any], Awaitable[dict[str, Any]]],
    ) -> LupMcpTool:
        sdk = SdkMcpTool(
            name=name,
            description=description,
            input_schema=input_model.model_json_schema(),
            handler=handler,
        )
        result: LupMcpTool = {
            "sdk_tool": sdk,
            "input_model": input_model,
        }
        if output_model is not None:
            result["output_model"] = output_model
        return result

    return decorator


def extract_sdk_tools(tools: list[LupMcpTool]) -> list[SdkMcpTool[Any]]:
    """Extract SdkMcpTool instances from a list of LupMcpTools.

    Use this when passing tools to ``create_mcp_server`` or
    ``create_sdk_mcp_server``, which expect ``list[SdkMcpTool]``.
    """
    return [t["sdk_tool"] for t in tools]


__all__ = [
    "LupMcpTool",
    "create_mcp_server",
    "create_sdk_mcp_server",
    "extract_sdk_tools",
    "lup_tool",
    "tool",
]
