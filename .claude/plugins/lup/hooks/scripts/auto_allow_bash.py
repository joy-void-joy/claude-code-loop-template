#!/usr/bin/env python3
"""PreToolUse hook that controls Bash permissions via regex patterns.

Rules are evaluated like .gitignore: all patterns are checked top-to-bottom,
and the last matching rule wins. If no rule matches, the decision falls
through to the user (ask).
"""

import json
import re
import sys

from typing import Literal

from pydantic import BaseModel, ValidationError


class Allow(BaseModel):
    action: Literal["allow"] = "allow"
    pattern: str
    reason: str = "Auto-allowed: command matches allowlist"


class Deny(BaseModel):
    action: Literal["deny"] = "deny"
    pattern: str
    reason: str = "Denied: command matches denylist"


# ---------------------------------------------------------------------------
# Configuration: rules evaluated top-to-bottom, last match wins
# ---------------------------------------------------------------------------

RULES: list[Allow | Deny] = [
    # Safe read-only / common commands
    Allow(pattern=r"^ls\b"),
    Allow(pattern=r"^tree\b"),
    Allow(pattern=r"^grep\b"),
    Allow(pattern=r"|\sxargs\b"),
    Allow(pattern=r"^test "),
    Allow(pattern=r"^find"),
    # GitHub CLI (read-only)
    Allow(pattern=r"^gh (pr|issue) (list|view|diff|status)\b"),
    # Git (safe subset)
    Allow(
        pattern=r"^git (status|log|diff|show|branch|worktree|stash|remote|fetch|tag|add|commit)\b"
    ),
    # uv package management
    Allow(pattern=r"^uv (sync|add|remove|lock)\b"),
    Allow(pattern=r"^uv run (pyright|pytest|ruff)\b"),
    Allow(pattern=r"^uv run \S+ --help$"),
    # lup-devtools CLI
    Allow(pattern=r"uv run lup-devtools\b"),
    # Block all python invocations...
    Deny(
        pattern=r"(^|\b)python3?\b",
        reason="Denied: use lup-devtools instead, or create a script in ./tmp/.",
    ),
    # ...except tmp scripts (overrides the deny above)
    Allow(pattern=r"^uv run (python )?(\./)?tmp/\S+\.py\b"),
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
    result: HookOutput | None = None

    for rule in RULES:
        if re.search(rule.pattern, cmd):
            if rule.action == "allow":
                result = _allow(rule.reason)
            else:
                result = _deny(rule.reason)

    return result


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
