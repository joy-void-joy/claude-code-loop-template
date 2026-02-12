"""MCP response formatting utilities.

Helper functions for creating properly formatted MCP tool responses.

The MCP response format is:
    {"content": [{"type": "text", "text": "..."}]}

For errors, add is_error=True:
    {"content": [{"type": "text", "text": "Error message"}], "is_error": True}
"""

import json
from typing import Any


def mcp_response(text: str, *, is_error: bool = False) -> dict[str, Any]:
    """Create an MCP response with text content.

    Args:
        text: The text content to return.
        is_error: Whether this is an error response.

    Returns:
        Properly formatted MCP response dict.
    """
    response: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        response["is_error"] = True
    return response


def mcp_success(result: Any) -> dict[str, Any]:
    """Create a successful MCP response with JSON-encoded result.

    Args:
        result: The data to return (will be JSON-serialized).

    Returns:
        MCP-formatted success response.

    Example:
        return mcp_success({"query": query, "results": results})
    """
    return mcp_response(json.dumps(result, default=str))


def mcp_error(message: str) -> dict[str, Any]:
    """Create an error MCP response.

    Args:
        message: Error message to return.

    Returns:
        MCP-formatted error response with is_error=True.

    Example:
        return mcp_error("Invalid query parameter")
    """
    return mcp_response(message, is_error=True)
