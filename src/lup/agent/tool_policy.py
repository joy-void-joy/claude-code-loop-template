"""Conditional tool availability based on configuration.

This is a TEMPLATE. Customize for your domain.

Key patterns:
1. Define tool sets as frozensets for fast membership testing
2. ToolPolicy class computes excluded tools at construction
3. from_settings() factory for easy initialization
4. Separate get_mcp_servers() and get_allowed_tools() methods

Usage:
    from lup.agent.config import settings
    from lup.agent.tool_policy import ToolPolicy

    policy = ToolPolicy.from_settings(settings)
    mcp_servers = policy.get_mcp_servers()
    allowed_tools = policy.get_allowed_tools()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, PrivateAttr, model_validator

if TYPE_CHECKING:
    from lup.agent.config import Settings


# =============================================================================
# TOOL SETS - Define tools that require specific API keys
# =============================================================================

# Built-in SDK tools (always available)
BUILTIN_TOOLS: frozenset[str] = frozenset(
    {
        "WebSearch",
        "WebFetch",
        "Read",
        "Write",
        "Glob",
        "Grep",
        "Bash",
        "Task",
    }
)

# Define named tool sets for each API dependency.
# Each set groups tools that share the same API key requirement.
# This makes it clear which tools degrade when a key is missing.
#
# Example:
# EXA_TOOLS: frozenset[str] = frozenset({
#     "mcp__search__search_exa",
# })
#
# FRED_TOOLS: frozenset[str] = frozenset({
#     "mcp__financial__fred_series",
#     "mcp__financial__fred_search",
# })


class ToolPolicy(BaseModel):
    """Centralized policy for tool availability.

    Determines which tools are available based on:
    - API key availability (from settings)
    - Mode configuration (e.g., restricted mode)
    - Session context (e.g., allow certain tools only in some contexts)

    Customize the model_validator to define your exclusion logic.
    """

    # API keys - add fields for your domain
    # exa_api_key: str | None = None
    # fred_api_key: str | None = None

    # Mode flags
    restricted_mode: bool = False

    # Computed excluded tools (populated by validator)
    _excluded_tools: frozenset[str] = PrivateAttr(default_factory=frozenset)

    @model_validator(mode="after")
    def compute_excluded_tools(self) -> Self:
        """Compute excluded tools based on configuration.

        Customize this for your domain's conditional tool availability.
        """
        excluded: set[str] = set()

        # TODO: Add your exclusion logic
        # Example:
        # if not self.exa_api_key:
        #     excluded.update(EXA_TOOLS)
        # if not self.fred_api_key:
        #     excluded.update(FRED_TOOLS)
        # if self.restricted_mode:
        #     excluded.update(LIVE_DATA_TOOLS)

        self._excluded_tools = frozenset(excluded)
        return self

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        restricted_mode: bool = False,
    ) -> ToolPolicy:
        """Create a ToolPolicy from application settings.

        Args:
            settings: Application settings with API keys.
            restricted_mode: If True, enables additional restrictions.

        Returns:
            ToolPolicy configured based on settings.
        """
        return cls(
            # TODO: Pass your API keys
            # exa_api_key=settings.exa_api_key,
            # fred_api_key=settings.fred_api_key,
            restricted_mode=restricted_mode,
        )

    def get_mcp_servers(self, *additional_servers: Any) -> dict[str, Any]:
        """Get MCP server configuration based on policy.

        Args:
            *additional_servers: Additional MCP servers to include.
                These should be McpSdkServerConfig objects.

        Returns:
            Dict mapping server name to server config.

        Customize this to return your domain's MCP servers.
        """
        servers: dict[str, Any] = {}

        # Add any additional servers passed in
        for server in additional_servers:
            name = getattr(server, "name", str(server))
            servers[name] = server

        # TODO: Add your MCP servers
        # Example:
        # servers["search"] = search_server
        # servers["financial"] = financial_server
        #
        # Conditional inclusion:
        # if not self.restricted_mode:
        #     servers["live_data"] = live_data_server

        return servers

    def get_allowed_tools(self) -> list[str]:
        """Get list of allowed tools based on policy.

        Returns:
            Sorted list of tool names that are allowed.
        """
        # Start with all potential tools
        tools: set[str] = set()

        # Built-in tools
        tools.update(BUILTIN_TOOLS)

        # TODO: Add your tool sets
        # tools.update(EXA_TOOLS)
        # tools.update(FRED_TOOLS)
        # tools.update(YOUR_DOMAIN_TOOLS)

        # Remove excluded tools
        tools -= self._excluded_tools

        return sorted(tools)

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a specific tool is available under this policy."""
        return tool_name not in self._excluded_tools
