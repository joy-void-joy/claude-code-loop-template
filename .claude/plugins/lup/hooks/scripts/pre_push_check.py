#!/usr/bin/env python3
"""Pre-push quality check hook.

Intercepts git push commands and runs pyright, ruff, and tests.
Auto-fixes formatting issues where possible.
"""

import json
import os
import sys
from pathlib import Path

import sh


def deny(message: str) -> None:
    """Output a deny response and exit."""
    response = {
        "hookSpecificOutput": {"permissionDecision": "deny"},
        "systemMessage": message,
    }
    print(json.dumps(response), file=sys.stderr)
    sys.exit(2)


def main() -> None:
    """Main hook logic."""
    # Read input from stdin
    input_data = json.loads(sys.stdin.read())

    # Extract command from tool input
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only intercept git push commands
    if not command.startswith("git push"):
        sys.exit(0)

    print(f"Pre-push checks triggered for: {command}", file=sys.stderr)

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    os.chdir(project_dir)

    # Check for uncommitted changes
    try:
        status = sh.git("status", "--porcelain").strip()
        if status:
            deny(
                "Cannot push: working tree has uncommitted changes. "
                "Please commit or stash changes first."
            )
    except sh.ErrorReturnCode as e:
        deny(f"Cannot check git status: {e.stderr.decode()}")

    print("Working tree is clean, running quality checks...", file=sys.stderr)

    # Track if we need to re-run checks after auto-fix
    needs_recheck = False

    # 1. Run pyright
    print("Running pyright...", file=sys.stderr)
    try:
        sh.uv("run", "pyright")
    except sh.ErrorReturnCode:
        deny("Cannot push: pyright found type errors. Please fix them before pushing.")
    print("pyright passed", file=sys.stderr)

    # 2. Run ruff format (auto-fix)
    print("Running ruff format...", file=sys.stderr)
    try:
        format_output = sh.uv("run", "ruff", "format", ".").strip()
        if format_output and "0 files" not in format_output:
            print(f"Ruff formatted files:\n{format_output}", file=sys.stderr)
            needs_recheck = True
    except sh.ErrorReturnCode:
        pass  # Formatting errors are not fatal

    # 3. Run ruff check with auto-fix
    print("Running ruff check...", file=sys.stderr)
    try:
        sh.uv("run", "ruff", "check", ".", "--fix")
    except sh.ErrorReturnCode:
        # Check if there are still errors after auto-fix
        try:
            sh.uv("run", "ruff", "check", ".")
        except sh.ErrorReturnCode:
            deny(
                "Cannot push: ruff found linting errors that could not be auto-fixed. "
                "Please fix them manually."
            )
        needs_recheck = True
    print("ruff check passed", file=sys.stderr)

    # 4. Run tests
    print("Running tests...", file=sys.stderr)
    try:
        sh.uv("run", "pytest")
    except sh.ErrorReturnCode:
        deny("Cannot push: tests failed. Please fix failing tests before pushing.")
    print("Tests passed", file=sys.stderr)

    # If we auto-fixed anything, check for new uncommitted changes
    if needs_recheck:
        try:
            status = sh.git("status", "--porcelain").strip()
            if status:
                deny(
                    "Cannot push: ruff auto-fixed some files. "
                    "Please review and commit the formatting changes, then try pushing again."
                )
        except sh.ErrorReturnCode:
            pass

    print("All checks passed! Allowing push.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
