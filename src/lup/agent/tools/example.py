"""Example MCP tools showing the pattern.

This is a TEMPLATE. Create your own tools following this pattern.

Key patterns from Claude Agent SDK docs:
1. Use @tool decorator with (name, description, input_schema)
2. Define input schemas as BaseModel with Field(description=...)
3. Use Model.model_json_schema() for @tool and Model.model_validate(args) inside
4. Return {"content": [{"type": "text", "text": "..."}]}
5. Tool names become: mcp__{server_name}__{tool_name}

Tool descriptions are the agent's only documentation for each tool.
A terse description forces the agent to guess when/why to use a tool,
which leads to misuse or underuse. A good description answers:
  - WHAT: What does this tool do? (concrete behavior)
  - WHEN: When should the agent use it? (triggers, conditions)
  - WHY: Why does this tool exist? (what problem it solves)
This keeps tool knowledge in the tool itself rather than in the prompt,
so descriptions stay accurate as tools are added or changed.
"""

import json
from typing import Any

from pydantic import BaseModel, Field

from claude_agent_sdk import tool

from lup.lib import tracked


# --- Input Schemas ---
# Define as BaseModel with Field(description=...) for validation + rich JSON Schema


class SearchInput(BaseModel):
    """Input for the search tool."""

    query: str = Field(description="Search query string")
    limit: int = Field(default=10, description="Maximum number of results to return")


class FetchInput(BaseModel):
    """Input for the fetch tool."""

    url: str = Field(description="URL to fetch content from")


# --- Tool Implementations ---
# Use Model.model_json_schema() for @tool, Model.model_validate(args) inside


@tool(
    "search_example",
    (
        "Search for information using keyword queries. "
        "Use this when the agent needs to find data that isn't available in local notes "
        "or when exploring a topic before making decisions. "
        "Exists because the agent has no built-in knowledge beyond its training data. "
        "Returns a JSON object with {query, results: [{title, url}], count}. "
        "Replace this with your actual search implementation."
    ),
    SearchInput.model_json_schema(),
)
@tracked("search_example")
async def search_example(args: dict[str, Any]) -> dict[str, Any]:
    """Search for information."""
    params = SearchInput.model_validate(args)

    if not params.query:
        return {
            "content": [{"type": "text", "text": "Error: Query is required"}],
            "is_error": True,
        }

    # TODO: Implement actual search logic
    # Example with a real search API:
    #
    # try:
    #     results = await search_api.search(params.query, limit=params.limit)
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
        "query": params.query,
        "results": [
            {"title": "Example Result 1", "url": "https://example.com/1"},
            {"title": "Example Result 2", "url": "https://example.com/2"},
        ],
        "count": 2,
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "fetch_example",
    (
        "Fetch the full content of a web page by URL. "
        "Use this when the agent has a specific URL to retrieve — e.g., from search "
        "results, a known reference, or a link found in notes. "
        "Exists because the agent cannot browse the web directly; this tool provides "
        "read access to individual pages. "
        "Returns a JSON object with {url, content, status}. "
        "Replace this with your actual fetch implementation."
    ),
    FetchInput.model_json_schema(),
)
@tracked("fetch_example")
async def fetch_example(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch content from a URL."""
    params = FetchInput.model_validate(args)

    if not params.url:
        return {
            "content": [{"type": "text", "text": "Error: URL is required"}],
            "is_error": True,
        }

    # TODO: Implement actual fetch logic
    # Example with httpx:
    #
    # try:
    #     async with httpx.AsyncClient() as client:
    #         response = await client.get(params.url)
    #         response.raise_for_status()
    #         result = {"url": params.url, "content": response.text[:5000], "status": 200}
    #         return {"content": [{"type": "text", "text": json.dumps(result)}]}
    # except Exception as e:
    #     return {
    #         "content": [{"type": "text", "text": f"Fetch failed: {e}"}],
    #         "is_error": True,
    #     }

    # Placeholder response
    result = {
        "url": params.url,
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
