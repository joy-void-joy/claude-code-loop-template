#!/usr/bin/env python3
"""PLAN.md existence check for git push.

Warns if PLAN.md doesn't exist when pushing a feature branch.
"""

import json
import os
import sys
from pathlib import Path

import sh


def main() -> None:
    """Main hook logic."""
    # Read input from stdin
    input_data = json.loads(sys.stdin.read())

    # Extract command from tool input
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check for git push commands
    if not command.startswith("git push"):
        sys.exit(0)

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    os.chdir(project_dir)

    # Check if we're on a feature branch
    try:
        current_branch = sh.git("branch", "--show-current").strip()
    except sh.ErrorReturnCode:
        sys.exit(0)

    if not current_branch.startswith("feat/"):
        # Not a feature branch, skip PLAN.md check
        sys.exit(0)

    # Check if PLAN.md exists
    if not (project_dir / "PLAN.md").exists():
        response = {
            "systemMessage": (
                "Warning: PLAN.md does not exist. "
                "Consider creating a PLAN.md that documents the feature implementation, "
                "its goals, and current status before pushing."
            )
        }
        print(json.dumps(response), file=sys.stderr)

    # Don't block, just warn
    sys.exit(0)


if __name__ == "__main__":
    main()
