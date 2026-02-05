"""Tools package - MCP tools and domain-specific utilities.

This package contains:
- example.py: Template MCP tools to customize for your domain
- (add your domain-specific tools here)

Utilities are re-exported from loop.lib for convenience:
- metrics: Tool call tracking with @tracked decorator
- retry: Retry decorator for API calls with exponential backoff
- cache: TTL-based caching for API responses
- responses: MCP response formatting utilities
"""

# Re-export utilities from lib for backward compatibility
from loop.lib import (
    MetricsCollector,
    ToolMetrics,
    TTLCache,
    api_cache,
    cached,
    clear_cache,
    get_cache_stats,
    get_metrics_summary,
    log_metrics_summary,
    mcp_error,
    mcp_response,
    mcp_success,
    reset_metrics,
    tracked,
    with_retry,
)

__all__ = [
    # Cache
    "TTLCache",
    "api_cache",
    "cached",
    "clear_cache",
    "get_cache_stats",
    # Metrics
    "MetricsCollector",
    "ToolMetrics",
    "get_metrics_summary",
    "log_metrics_summary",
    "reset_metrics",
    "tracked",
    # Responses
    "mcp_error",
    "mcp_response",
    "mcp_success",
    # Retry
    "with_retry",
]
