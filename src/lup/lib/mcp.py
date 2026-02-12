"""MCP server utilities.

Re-exports create_sdk_mcp_server from the Claude Agent SDK with usage examples.

Usage:
    from claude_agent_sdk import tool, create_sdk_mcp_server

    @tool("my_tool", "Description", {"param": str})
    async def my_tool(args: dict) -> dict:
        return {"content": [{"type": "text", "text": "result"}]}

    server = create_sdk_mcp_server(
        name="my-server",
        version="1.0.0",
        tools=[my_tool]
    )

    # In ClaudeAgentOptions:
    options = ClaudeAgentOptions(
        mcp_servers={"my-server": server},
        allowed_tools=["mcp__my-server__my_tool"],
    )

Tool naming convention:
    After registration, tools are named: mcp__{server_name}__{tool_name}
    Example: mcp__my-server__my_tool
"""

# Re-export from SDK for convenience
from claude_agent_sdk import create_sdk_mcp_server, tool

__all__ = ["create_sdk_mcp_server", "tool"]
