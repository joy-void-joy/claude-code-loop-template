#!/usr/bin/env python3
"""PreToolUse hook that controls WebFetch permissions via regex patterns.

Decision order:
1. Check URL against DENY_PATTERNS -> deny with reason
2. Check URL against ALLOW_PATTERNS -> auto-allow
3. Fall through -> defer to user (ask)
"""

import json
import re
import sys

from pydantic import BaseModel, ValidationError

# ---------------------------------------------------------------------------
# Configuration: edit these lists to control WebFetch permissions
# ---------------------------------------------------------------------------

ALLOW_PATTERNS: list[str] = [
    # Project documentation
    r"https?://docs\.claude\.com/",
    r"https?://ai\.pydantic\.dev/",
]

DENY_PATTERNS: list[tuple[str, str]] = [
    # (pattern, reason)
    # Example:
    # (r"https?://malicious\.example\.com", "Blocked: known malicious domain"),
]

# ---------------------------------------------------------------------------
# Hook implementation
# ---------------------------------------------------------------------------

HookOutput = dict[str, dict[str, str]]


class WebFetchInput(BaseModel):
    url: str = ""
    prompt: str = ""


class HookEvent(BaseModel):
    tool_name: str = ""
    tool_input: WebFetchInput = WebFetchInput()


def _allow(reason: str = "Auto-allowed: URL matches allowlist") -> HookOutput:
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


def decide(url: str) -> HookOutput | None:
    for pattern, reason in DENY_PATTERNS:
        if re.search(pattern, url):
            return _deny(reason)

    for pattern in ALLOW_PATTERNS:
        if re.search(pattern, url):
            return _allow()

    return None


def main() -> None:
    try:
        event = HookEvent.model_validate_json(sys.stdin.read())
    except (ValidationError, OSError):
        sys.exit(0)

    if event.tool_name != "WebFetch":
        sys.exit(0)

    result = decide(event.tool_input.url)
    if result:
        json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
