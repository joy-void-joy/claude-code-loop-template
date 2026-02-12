"""Hook utilities for the Claude Agent SDK.

This is a TEMPLATE. Add hooks for your domain's needs.

Key patterns:
1. HooksConfig TypedDict for type-safe hook configuration
2. merge_hooks() to compose multiple hook sources
3. create_permission_hooks() for directory-based access control
4. Post-tool hooks for response inspection/injection

Usage:
    from lup.lib import merge_hooks, create_permission_hooks, HooksConfig

    permission_hooks = create_permission_hooks(rw_dirs, ro_dirs)
    custom_hooks = create_my_custom_hooks()
    combined = merge_hooks(permission_hooks, custom_hooks)

    options = ClaudeAgentOptions(hooks=combined, ...)
"""

from pathlib import Path
from typing import Any, Literal, TypedDict

from claude_agent_sdk import HookMatcher
from claude_agent_sdk.types import HookContext

from lup.lib.notes import path_is_under


# Hook event types supported by the Claude Agent SDK
HookEventType = Literal[
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
]


class HooksConfig(TypedDict, total=False):
    """Typed hook configuration for ClaudeAgentOptions.

    Each key is a hook event type, and the value is a list of HookMatcher
    instances that will be invoked for that event.
    """

    PreToolUse: list[HookMatcher]
    PostToolUse: list[HookMatcher]
    PostToolUseFailure: list[HookMatcher]
    UserPromptSubmit: list[HookMatcher]
    Stop: list[HookMatcher]
    SubagentStop: list[HookMatcher]
    PreCompact: list[HookMatcher]


def merge_hooks(base: HooksConfig, additional: HooksConfig) -> HooksConfig:
    """Merge two hook configurations.

    For each hook event type, combines the matchers from both configs.
    Base hooks run first, then additional hooks.

    Args:
        base: The base hook configuration.
        additional: Hook configuration to merge into base.

    Returns:
        New HooksConfig with combined matchers.
    """
    merged: HooksConfig = dict(base)  # type: ignore[assignment]

    for event in additional:
        if event in merged:
            merged[event] = merged[event] + additional[event]  # type: ignore[literal-required]
        else:
            merged[event] = additional[event]  # type: ignore[literal-required]

    return merged


def create_permission_hooks(
    rw_dirs: list[Path],
    ro_dirs: list[Path],
) -> HooksConfig:
    """Create permission hooks with directory-based access control.

    Controls Read/Write/Edit/Glob/Grep access based on directory permissions:
    - Write/Edit: Only allowed in rw_dirs
    - Read/Glob/Grep: Allowed in rw_dirs + ro_dirs
    - Other tools: Allowed (filtered by allowed_tools in options)

    Args:
        rw_dirs: Directories where Write/Edit/Read are allowed.
        ro_dirs: Additional directories where only Read is allowed.

    Returns:
        Hooks configuration dict for ClaudeAgentOptions.
    """
    all_readable = rw_dirs + ro_dirs

    async def permission_hook(
        input_data: Any,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> dict[str, Any]:
        """Control tool access based on directory permissions."""
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        hook_event = input_data["hook_event_name"]

        def deny(reason: str) -> dict[str, Any]:
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }

        def allow() -> dict[str, Any]:
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event,
                    "permissionDecision": "allow",
                }
            }

        # Write: allow in RW directories only
        if tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            if not file_path:
                return {}  # Let SDK handle missing required param
            if path_is_under(file_path, rw_dirs):
                return allow()
            return deny(f"Write denied. Allowed: {[str(d) for d in rw_dirs]}")

        # Edit: only allowed in RW directories
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            if not file_path:
                return {}
            if path_is_under(file_path, rw_dirs):
                return allow()
            return deny(f"Edit denied. Allowed: {[str(d) for d in rw_dirs]}")

        # Read: must be in readable directories
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if not file_path:
                return {}
            if path_is_under(file_path, all_readable):
                return allow()
            return deny(f"Read denied. Allowed: {[str(d) for d in all_readable]}")

        # Glob/Grep: require explicit path in readable directories
        if tool_name in ("Glob", "Grep"):
            file_path = tool_input.get("path", "")
            if not file_path:
                return deny(
                    f"Path required for {tool_name}. "
                    f"Specify path in: {[str(d) for d in all_readable]}"
                )
            if path_is_under(file_path, all_readable):
                return allow()
            return deny(
                f"{tool_name} denied. Allowed: {[str(d) for d in all_readable]}"
            )

        # Auto-allow everything else
        return allow()

    return {
        "PreToolUse": [HookMatcher(hooks=[permission_hook])],  # type: ignore[list-item]
    }


# =============================================================================
# EXAMPLE: Post-tool hook for response inspection
# =============================================================================


def create_post_tool_hooks() -> HooksConfig:
    """Example: Create post-tool hooks for response inspection.

    Customize this for your domain. Common uses:
    - Detect poor-quality WebFetch responses (JS-rendered garbage)
    - Inject system messages with alternative suggestions
    - Log tool responses for debugging

    Returns:
        Hooks configuration for PostToolUse events.
    """

    async def example_post_hook(
        input_data: Any,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> dict[str, Any]:
        """Example post-tool hook."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_response = input_data.get("tool_response", {})

        # Example: detect WebFetch issues
        if tool_name == "WebFetch":
            content = ""
            if isinstance(tool_response, str):
                content = tool_response
            elif isinstance(tool_response, dict):
                content = str(tool_response.get("content", ""))

            # Check for signs of JS-rendered garbage
            if len(content) < 100 and "loading" in content.lower():
                return {
                    "systemMessage": (
                        "The WebFetch response appears to be a JS-rendered page "
                        "that didn't load properly. Consider using a different "
                        "tool or URL."
                    )
                }

        return {}

    return {
        "PostToolUse": [HookMatcher(hooks=[example_post_hook])],  # type: ignore[list-item]
    }
