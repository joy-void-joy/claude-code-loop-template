#!/usr/bin/env python3
"""Test file protection hook.

- Hard blocks test file edits when TDD mode is active (flag file exists)
- Warns about test file edits when TDD mode is not active

This enforces TDD discipline: tests are written first, implementation follows.
"""

import json
import os
import re
import sys
from pathlib import Path


def is_test_file(file_path: str) -> bool:
    """Check if the given path is a test file."""
    path = Path(file_path)
    filename = path.name

    # Pattern 1: test_*.py
    if re.match(r"^test_.*\.py$", filename):
        return True

    # Pattern 2: *_test.py
    if re.match(r"^.*_test\.py$", filename):
        return True

    # Pattern 3: conftest.py
    if filename == "conftest.py":
        return True

    # Pattern 4: file is in tests/ directory
    if "/tests/" in str(path) or str(path).startswith("tests/"):
        return True

    return False


def main() -> None:
    """Main hook logic."""
    # Read input from stdin
    input_data = json.loads(sys.stdin.read())

    # Extract file path from tool input
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # If no file path, allow (probably not a file operation)
    if not file_path:
        sys.exit(0)

    # If not a test file, allow without comment
    if not is_test_file(file_path):
        sys.exit(0)

    # It's a test file - check if TDD mode is active
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    tdd_flag_file = Path(project_dir) / ".tdd-mode"

    if tdd_flag_file.exists():
        # TDD mode is active - HARD BLOCK test edits
        response = {
            "hookSpecificOutput": {"permissionDecision": "deny"},
            "systemMessage": (
                f"BLOCKED: Cannot modify test files during TDD implementation phase. "
                f"Test file: {file_path}. "
                "If tests need changes, return a detailed analysis report explaining "
                "what modifications are needed and why, then exit to let the user make the changes."
            ),
        }
        print(json.dumps(response), file=sys.stderr)
        sys.exit(2)

    # TDD mode not active - require user permission
    response = {
        "hookSpecificOutput": {"permissionDecision": "ask"},
        "systemMessage": (
            f"Test file modification requested: {file_path}. "
            "This requires explicit user approval. "
            "Please confirm you want to modify this test file."
        ),
    }
    print(json.dumps(response), file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
