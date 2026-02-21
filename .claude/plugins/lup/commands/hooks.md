---
allowed-tools: Read, Edit, Grep, Glob, AskUserQuestion
description: View and modify permission hook patterns (bash, fetch, edits)
---

# Hooks: Permission Hook Management

Modify the PreToolUse permission hooks that control auto-allow, auto-deny, and ask behavior.

## User's Request

$ARGUMENTS

## Hook Files

The configurable hooks live in `.claude/plugins/lup/hooks/scripts/`:

| File                  | Controls        | Configurable Parts                                                                 |
| --------------------- | --------------- | ---------------------------------------------------------------------------------- |
| `auto_allow_bash.py`  | Bash commands   | `RULES` list of `Allow`/`Deny` (last-match-wins)                                   |
| `auto_allow_fetch.py` | WebFetch URLs   | `ALLOW_PATTERNS` (list of regex), `DENY_PATTERNS` (list of (regex, reason) tuples) |
| `auto_allow_edits.py` | Edit operations | `PROTECTED_PATTERNS` (list of regex), `MAX_REAL_CHANGES` (int)                     |

Other hooks (`pre_push_check.py`, `check_plan_md.py`, `protect_tests.py`) are structural and not managed here.

## How It Works

- **ALLOW_PATTERNS / Allow rules**: Commands/URLs matching these are auto-approved (no user prompt)
- **DENY_PATTERNS / Deny rules**: Commands/URLs matching these are blocked with a reason message
- **Neither**: Falls through to ask the user interactively
- **PROTECTED_PATTERNS** (edits only): Files matching these always defer to user
- **MAX_REAL_CHANGES** (edits only): Edits with more nontrivial lines than this defer to user

## Your Task

1. **Read all 3 hook scripts** to see current patterns
2. **Parse the user's request** to determine:
   - Which hook file to modify
   - Which list to modify (allow, deny, protected)
   - What pattern to add or remove
3. **Show the user** the current relevant patterns and propose the specific edit
4. **Use AskUserQuestion** to confirm before making the change
5. **Make the edit** using the Edit tool

## Guidelines

- Patterns are Python regex strings (raw strings with `r"..."` prefix)
- For DENY_PATTERNS, always include a helpful reason message
- When adding allow patterns, prefer precise patterns over broad ones (e.g., `r"^npm run build$"` not `r"^npm"`)
- When the user's request is ambiguous about which hook, ask
- Show the exact pattern you'll add so the user can verify the regex

## Examples

User says: "allow fetching from pypi.org"
-> Add `r"https?://pypi\.org/"` to `auto_allow_fetch.py` ALLOW_PATTERNS

User says: "auto-approve docker compose commands"
-> Add `Allow(r"^docker compose\b")` to `auto_allow_bash.py` RULES

User says: "block rm -rf commands"
-> Add `Deny(r"^rm -rf\b", "Denied: rm -rf is blocked for safety.")` to `auto_allow_bash.py` RULES

User says: "protect the settings/ directory from edits"
-> Add `r"(^|/)settings/"` to `auto_allow_edits.py` PROTECTED_PATTERNS

User says: "increase the edit threshold to 5 lines"
-> Change `MAX_REAL_CHANGES = 3` to `MAX_REAL_CHANGES = 5` in `auto_allow_edits.py`

User says: "remove the pypi allow pattern"
-> Remove the matching pattern from the relevant list

## If no arguments provided

If `$ARGUMENTS` is empty, read all 3 hook files and present a summary of current configuration using this format:

### Bash (auto_allow_bash.py)

**Rules:** (list Allow/Deny rules in order)

### Fetch (auto_allow_fetch.py)

**Auto-allow:** (list patterns)
**Deny:** (list patterns with reasons)

### Edits (auto_allow_edits.py)

**Protected files:** (list patterns)
**Max real changes:** N

Then ask what the user wants to change.
