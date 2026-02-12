#!/usr/bin/env python3
"""PreToolUse hook that auto-allows small, safe Edit operations.

Decision order:
1. Protected files (.claude/, pyproject.toml, .env*) -> always defer
2. Pure deletion (new_string is empty) -> allow
3. replace_all: single-line rename -> allow, multi-line -> defer
4. Count nontrivial added lines (using a state machine for context-aware
   classification) -> allow if <= MAX_REAL_CHANGES
"""

import difflib
import json
import re
import sys

from pydantic import BaseModel, ValidationError

MAX_REAL_CHANGES = 3

PROTECTED_PATTERNS = [
    r"(^|/)\.claude/",
    r"(^|/)pyproject\.toml$",
    r"(^|/)\.env($|\.)",
]


def is_protected_file(file_path: str) -> bool:
    return any(re.search(p, file_path) for p in PROTECTED_PATTERNS)


def _is_trivial_content(stripped: str) -> bool:
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if stripped.startswith("import ") or stripped.startswith("from "):
        return True
    if stripped == "pass":
        return True
    return False


def _classify_trivial(lines: list[str]) -> list[bool]:
    result: list[bool] = []
    in_docstring = False
    docstring_delim = ""
    in_import = False
    in_type_def = False
    type_def_indent = 0

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip()) if stripped else 0

        if in_docstring:
            result.append(True)
            if docstring_delim in stripped:
                in_docstring = False
            continue

        if in_import:
            result.append(True)
            if ")" in stripped:
                in_import = False
            continue

        for delim in ('"""', "'''"):
            if delim in stripped:
                if stripped.count(delim) == 1:
                    in_docstring = True
                    docstring_delim = delim
                result.append(True)
                break
        else:
            if (
                _is_trivial_content(stripped)
                and "(" in stripped
                and ")" not in stripped
            ):
                in_import = True
                result.append(True)
                continue

            if in_type_def and stripped and indent <= type_def_indent:
                in_type_def = False

            m = re.match(
                r"(\s*)class\s+\w+\s*\(.*(?:TypedDict|BaseModel).*\)\s*:", line
            )
            if m:
                in_type_def = True
                type_def_indent = len(m.group(1))
                result.append(True)
            elif in_type_def:
                result.append(True)
            else:
                result.append(_is_trivial_content(stripped))

    return result


def count_real_additions(old_string: str, new_string: str) -> int:
    old_lines = old_string.splitlines() if old_string else []
    new_lines = new_string.splitlines() if new_string else []

    matcher = difflib.SequenceMatcher(
        None,
        [ln.strip() for ln in old_lines],
        [ln.strip() for ln in new_lines],
    )

    added_indices: set[int] = set()
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            added_indices.update(range(j1, j2))

    if not added_indices:
        return 0

    trivial = _classify_trivial(new_lines)
    return sum(1 for j in added_indices if not trivial[j])


AllowDecision = dict[str, dict[str, str]]


class EditInput(BaseModel):
    file_path: str = ""
    old_string: str = ""
    new_string: str = ""
    replace_all: bool = False


class HookEvent(BaseModel):
    tool_name: str = ""
    tool_input: EditInput = EditInput()


def _allow_decision() -> AllowDecision:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Auto-allowed: safe edit pattern detected",
        }
    }


def decide(tool_input: EditInput) -> AllowDecision | None:
    file_path = tool_input.file_path
    old_string = tool_input.old_string
    new_string = tool_input.new_string
    replace_all = tool_input.replace_all

    if is_protected_file(file_path):
        return None

    if old_string and not new_string:
        return _allow_decision()

    if replace_all:
        old_n = len(old_string.splitlines()) if old_string else 0
        new_n = len(new_string.splitlines()) if new_string else 0
        if old_n <= 1 and new_n <= 1:
            return _allow_decision()
        return None

    if count_real_additions(old_string, new_string) <= MAX_REAL_CHANGES:
        return _allow_decision()

    return None


def main() -> None:
    try:
        event = HookEvent.model_validate_json(sys.stdin.read())
    except (ValidationError, OSError):
        sys.exit(0)

    if event.tool_name != "Edit":
        sys.exit(0)

    result = decide(event.tool_input)
    if result:
        json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
