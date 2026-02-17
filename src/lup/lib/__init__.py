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

Domain-specific code belongs in lup.agent, not here.
"""

from lup.lib.cache import TTLCache, api_cache, cached, clear_cache, get_cache_stats
from lup.lib.history import (
    format_history_for_context,
    get_latest_session,
    list_all_sessions,
    load_sessions,
    save_session,
    update_session_metadata,
)
from lup.lib.hooks import (
    HookEventType,
    HooksConfig,
    create_permission_hooks,
    create_post_tool_hooks,
    create_tool_allowlist_hook,
    merge_hooks,
)
from lup.lib.mcp import create_sdk_mcp_server, tool
from lup.lib.metrics import (
    MetricsCollector,
    ToolMetrics,
    get_metrics_summary,
    log_metrics_summary,
    reset_metrics,
    tracked,
)
from lup.lib.notes import NotesConfig, path_is_under, setup_notes
from lup.lib.realtime import (
    ActionCallback,
    DebounceInput,
    RemindInput,
    ScheduleActionInput,
    Scheduler,
    SleepInput,
    create_meta_before_sleep_guard,
    create_pending_event_guard,
    create_stop_guard,
)
from lup.lib.responses import mcp_error, mcp_response, mcp_success
from lup.lib.scoring import (
    append_score_row,
    read_scores_csv,
    read_scores_for_task,
    read_scores_for_version,
    rebuild_scores_csv,
)
from lup.lib.retry import with_retry
from lup.lib.trace import (
    TraceEntry,
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
    "create_tool_allowlist_hook",
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
    # Realtime
    "ActionCallback",
    "DebounceInput",
    "RemindInput",
    "ScheduleActionInput",
    "Scheduler",
    "SleepInput",
    "create_meta_before_sleep_guard",
    "create_pending_event_guard",
    "create_stop_guard",
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
    "TraceEntry",
    "TraceLogger",
    "format_block_markdown",
    "normalize_content",
    "print_block",
    "truncate_content",
]
