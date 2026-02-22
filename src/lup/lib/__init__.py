"""Library utilities for self-improving agents.

This package contains reusable, **parametric** abstractions that work
out of the box and are configured through function arguments — never
by modifying the source. Domain-specific code belongs in lup.agent.

Modules:
- client: Centralized Agent SDK client creation (build_client, run_query, one_shot)
- history: Session history storage and retrieval (generic, model-agnostic)
- hooks: Claude Agent SDK hook utilities (permission, nudge, capture)
- metrics: Tool call tracking with @tracked decorator
- mcp: MCP server creation utilities
- notes: RO/RW notes directory structure
- paths: Centralized path constants (configurable via configure())
- realtime: Scheduler for persistent agents (sleep/wake, debounce, reminders)
- reflect: Reflection gate (enforce reflect-before-output)
- responses: MCP response formatting utilities
- retry: Retry decorator for API calls
- sandbox: Docker-based Python sandbox for isolated code execution
"""

from lup.lib.client import build_client, one_shot, run_query, save_images
from lup.lib.history import (
    format_history_for_context,
    get_latest_session_json,
    list_all_sessions,
    load_sessions_json,
    save_session,
    update_session_metadata,
)
from lup.lib.hooks import (
    HookEventType,
    HooksConfig,
    NudgeCheck,
    create_capture_hook,
    create_nudge_hook,
    create_permission_hooks,
    create_tool_allowlist_hook,
    merge_hooks,
)
from lup.lib.mcp import (
    LupMcpTool,
    create_sdk_mcp_server,
    extract_sdk_tools,
    lup_tool,
    tool,
)
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
from lup.lib.reflect import ReflectionGate, create_reflection_gate
from lup.lib.responses import mcp_error, mcp_response, mcp_success
from lup.lib.retry import with_retry
from lup.lib.sandbox import (
    CodeExecutionTimeoutError,
    Sandbox,
    SandboxNotInitializedError,
)
from lup.lib.trace import (
    ResponseCollector,
    TraceEntry,
    TraceLogger,
    format_block_markdown,
    format_tool_result,
    normalize_content,
    print_block,
    truncate_content,
)

__all__ = [
    # Client
    "build_client",
    "one_shot",
    "run_query",
    "save_images",
    # History
    "format_history_for_context",
    "get_latest_session_json",
    "list_all_sessions",
    "load_sessions_json",
    "save_session",
    "update_session_metadata",
    # Hooks
    "HookEventType",
    "HooksConfig",
    "NudgeCheck",
    "create_capture_hook",
    "create_nudge_hook",
    "create_permission_hooks",
    "create_tool_allowlist_hook",
    "merge_hooks",
    # MCP
    "LupMcpTool",
    "create_sdk_mcp_server",
    "extract_sdk_tools",
    "lup_tool",
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
    # Reflect
    "ReflectionGate",
    "create_reflection_gate",
    # Responses
    "mcp_error",
    "mcp_response",
    "mcp_success",
    # Retry
    "with_retry",
    # Sandbox
    "CodeExecutionTimeoutError",
    "Sandbox",
    "SandboxNotInitializedError",
    # Trace
    "ResponseCollector",
    "TraceEntry",
    "TraceLogger",
    "format_block_markdown",
    "format_tool_result",
    "normalize_content",
    "print_block",
    "truncate_content",
]
