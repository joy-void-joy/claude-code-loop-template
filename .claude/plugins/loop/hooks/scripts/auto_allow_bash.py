#!/usr/bin/env python3
"""PreToolUse hook that controls Bash permissions via regex patterns.

Decision order:
1. Check command against DENY_PATTERNS -> deny with reason
2. Check command against ALLOW_PATTERNS -> auto-allow
3. Fall through -> defer to user (ask)
"""

import json
import re
import sys

from pydantic import BaseModel, ValidationError

# ---------------------------------------------------------------------------
# Configuration: edit these lists to control Bash permissions
# ---------------------------------------------------------------------------

ALLOW_PATTERNS: list[str] = [
    r"^ls\b",
    r"^grep\b",
    r"^git (status|log|diff|show|branch|worktree|stash|remote|fetch|tag|add|commit)\b",
    r"^uv (sync|add|remove|lock)\b",
    r"^uv run (pyright|pytest|ruff)\b",
    r"^uv run \S+ --help$",
    r"^uv run (python )?\.claude/plugins/loop/scripts/",
    r"^uv run (python )?\./tmp/\S+\.py\b",
]

DENY_PATTERNS: list[tuple[str, str]] = [
    # Block inline python execution -- create a script instead
    (
        r"^uv run python3? -c",
        "Denied: inline python -c is not allowed. Create a script in .claude/plugins/loop/scripts/ or ./tmp/ instead.",
    ),
    (
        r"^uv run python3? <<",
        "Denied: heredoc python is not allowed. Create a script in .claude/plugins/loop/scripts/ or ./tmp/ instead.",
    ),
    (
        r"^python3? ",
        "Denied: bare python is not allowed. Use 'uv run python' or create a script in .claude/plugins/loop/scripts/.",
    ),
]

# ---------------------------------------------------------------------------
# Hook implementation
# ---------------------------------------------------------------------------

HookOutput = dict[str, dict[str, str]]


class BashInput(BaseModel):
    command: str = ""
    description: str = ""
    timeout: int | None = None
    run_in_background: bool = False


class HookEvent(BaseModel):
    tool_name: str = ""
    tool_input: BashInput = BashInput()


def _allow(reason: str = "Auto-allowed: command matches allowlist") -> HookOutput:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }


def _deny(reason: str) -> HookOutput:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def decide(command: str) -> HookOutput | None:
    cmd = command.strip()

    for pattern, reason in DENY_PATTERNS:
        if re.search(pattern, cmd):
            return _deny(reason)

    for pattern in ALLOW_PATTERNS:
        if re.search(pattern, cmd):
            return _allow()

    return None


def main() -> None:
    try:
        event = HookEvent.model_validate_json(sys.stdin.read())
    except (ValidationError, OSError):
        sys.exit(0)

    if event.tool_name != "Bash":
        sys.exit(0)

    result = decide(event.tool_input.command)
    if result:
        json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
