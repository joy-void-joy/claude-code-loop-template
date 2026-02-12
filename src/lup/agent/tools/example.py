"""Example MCP tools showing the pattern.

This is a TEMPLATE. Create your own tools following this pattern.

Key patterns from Claude Agent SDK docs:
1. Use @tool decorator with (name, description, input_schema)
2. Input schema is simple type mapping: {"param": type}
3. Return {"content": [{"type": "text", "text": "..."}]}
4. Tool names become: mcp__{server_name}__{tool_name}
"""

import json
from typing import Any

from claude_agent_sdk import tool

from lup.lib import tracked


# --- Tool Implementations ---
# Use @tool(name, description, input_schema) pattern


@tool(
    "search_example",
    "Example search tool. Replace with your actual search implementation.",
    {"query": str, "limit": int},
)
@tracked("search_example")
async def search_example(args: dict[str, Any]) -> dict[str, Any]:
    """Search for information.

    Args:
        args: Dict with "query" and "limit" keys.

    Returns:
        MCP response with search results.
    """
    query = args.get("query", "")

    if not query:
        return {
            "content": [{"type": "text", "text": "Error: Query is required"}],
            "is_error": True,
        }

    # TODO: Implement actual search logic
    # Example with a real search API:
    #
    # try:
    #     results = await search_api.search(query, limit=limit)
    #     return {
    #         "content": [{"type": "text", "text": json.dumps(results)}]
    #     }
    # except Exception as e:
    #     return {
    #         "content": [{"type": "text", "text": f"Search failed: {e}"}],
    #         "is_error": True,
    #     }

    # Placeholder response
    result = {
        "query": query,
        "results": [
            {"title": "Example Result 1", "url": "https://example.com/1"},
            {"title": "Example Result 2", "url": "https://example.com/2"},
        ],
        "count": 2,
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "fetch_example",
    "Example fetch tool. Replace with your actual fetch implementation.",
    {"url": str},
)
@tracked("fetch_example")
async def fetch_example(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch content from a URL.

    Args:
        args: Dict with "url" key.

    Returns:
        MCP response with fetched content.
    """
    url = args.get("url", "")

    if not url:
        return {
            "content": [{"type": "text", "text": "Error: URL is required"}],
            "is_error": True,
        }

    # TODO: Implement actual fetch logic
    # Example with httpx:
    #
    # try:
    #     async with httpx.AsyncClient() as client:
    #         response = await client.get(url)
    #         response.raise_for_status()
    #         result = {"url": url, "content": response.text[:5000], "status": 200}
    #         return {"content": [{"type": "text", "text": json.dumps(result)}]}
    # except Exception as e:
    #     return {
    #         "content": [{"type": "text", "text": f"Fetch failed: {e}"}],
    #         "is_error": True,
    #     }

    # Placeholder response
    result = {
        "url": url,
        "content": "Example content from the URL",
        "status": 200,
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


# --- Tool Collection ---
# Group tools for your MCP server

EXAMPLE_TOOLS = [
    search_example,
    fetch_example,
]
"""List of example tools for the example MCP server."""
