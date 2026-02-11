"""Library utilities for self-improving agents.

This package contains reusable abstractions that rarely change:
- cache: TTL-based caching for API responses
- history: Session history storage and retrieval
- hooks: Claude Agent SDK hook utilities
- metrics: Tool call tracking with @tracked decorator
- mcp: MCP server creation utilities
- notes: RO/RW notes directory structure
- responses: MCP response formatting utilities
- retry: Retry decorator for API calls

Domain-specific code belongs in loop.agent, not here.
"""

from loop.lib.cache import TTLCache, api_cache, cached, clear_cache, get_cache_stats
from loop.lib.history import (
    format_history_for_context,
    get_latest_session,
    list_all_sessions,
    load_sessions,
    save_session,
    update_session_metadata,
)
from loop.lib.hooks import (
    HookEventType,
    HooksConfig,
    create_permission_hooks,
    create_post_tool_hooks,
    merge_hooks,
)
from loop.lib.mcp import create_sdk_mcp_server, tool
from loop.lib.metrics import (
    MetricsCollector,
    ToolMetrics,
    get_metrics_summary,
    log_metrics_summary,
    reset_metrics,
    tracked,
)
from loop.lib.notes import NotesConfig, path_is_under, setup_notes
from loop.lib.responses import mcp_error, mcp_response, mcp_success
from loop.lib.scoring import (
    append_score_row,
    read_scores_csv,
    read_scores_for_task,
    read_scores_for_version,
    rebuild_scores_csv,
)
from loop.lib.retry import with_retry
from loop.lib.trace import (
    TraceLogger,
    format_block_markdown,
    normalize_content,
    print_block,
    truncate_content,
)

__all__ = [
    # Cache
    "TTLCache",
    "api_cache",
    "cached",
    "clear_cache",
    "get_cache_stats",
    # History
    "format_history_for_context",
    "get_latest_session",
    "list_all_sessions",
    "load_sessions",
    "save_session",
    "update_session_metadata",
    # Hooks
    "HookEventType",
    "HooksConfig",
    "create_permission_hooks",
    "create_post_tool_hooks",
    "merge_hooks",
    # MCP
    "create_sdk_mcp_server",
    "tool",
    # Metrics
    "MetricsCollector",
    "ToolMetrics",
    "get_metrics_summary",
    "log_metrics_summary",
    "reset_metrics",
    "tracked",
    # Notes
    "NotesConfig",
    "path_is_under",
    "setup_notes",
    # Responses
    "mcp_error",
    "mcp_response",
    "mcp_success",
    # Retry
    "with_retry",
    # Scoring
    "append_score_row",
    "read_scores_csv",
    "read_scores_for_task",
    "read_scores_for_version",
    "rebuild_scores_csv",
    # Trace
    "TraceLogger",
    "format_block_markdown",
    "normalize_content",
    "print_block",
    "truncate_content",
]
