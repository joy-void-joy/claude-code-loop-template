# CLAUDE.md Template

Use this as a starting point for your project's CLAUDE.md. Customize each section for your domain.

---

# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

**Note:** Modifying `CLAUDE.md` means modifying `.claude/CLAUDE.md` (this file).

## Project Overview

**[Describe your agent and what it does]**

Built with Python 3.13+ and the Claude Agent SDK. Uses `uv` as the package manager.

### Naming Convention

- **Claude** = the meta-agent (Claude Code) that modifies the codebase, runs commands, and manages the development workflow
- **Lup** = the SDK agent inside the code being built and improved — the agent that runs via the CLI and produces outputs

When writing docs or prompts, use "Claude" when referring to the outer development agent and "Lup" (or your project name) when referring to the inner SDK agent.

### Important Context

**[Add domain-specific context here. Examples:]**
- What outcomes matter and how they're measured
- What data sources are available
- What constraints or limitations exist

---

# Getting Started

## Reference Files

- **src/<project>/agent/core.py**: Main agent orchestration
- **src/<project>/agent/subagents.py**: Subagent definitions
- **src/<project>/agent/tools/**: Tool implementations
- **src/<project>/environment/cli/__main__.py**: CLI application
- **src/<project>/devtools/**: Development and analysis CLI (lup-devtools)

## Commands

```bash
# Install dependencies
uv sync

# Run a single agent session
uv run python -m <project>.environment.cli run "your task here"

# Run multiple sessions with auto-commit
uv run python -m <project>.environment.cli loop "task1" "task2" "task3"

# Commit uncommitted session results
uv run lup-devtools git commit-results

# Add a new dependency
uv add <package-name>

# Format and lint
uv run ruff format .
uv run ruff check .
uv run pyright

# Run tests
uv run pytest
```

## Debugging

**Do not hypothesize -- trace.** When debugging errors, find the actual logs and read the exact exception. Do not list "likely causes" or suggest the user check things. Open the log files yourself, grep for the error, read the traceback, and report what actually happened.

Use `/lup:debug <error message>` to trace an error through the logs automatically.

## Feedback Loop

```bash
# Collect feedback from sessions
uv run lup-devtools feedback collect --all-time

# Analyze traces
uv run lup-devtools trace list
uv run lup-devtools trace show <session_id>

# Aggregate metrics
uv run lup-devtools metrics summary
```

---

# Development Workflow

## Git Workflow

This project uses **git worktrees** (not regular branches) to develop multiple features in parallel.

**IMPORTANT:** Never commit _code_ directly to `main`. Always work in a worktree for code changes.

### Commit Guidelines

- **Commit before responding** -- Always commit your work before responding to the user.
- **Commit early, commit often** -- Frequent commits provide checkpoints and make rebasing easier.
- **Keep commits atomic** -- Each commit should do one thing.

Use conventional commit syntax: `type(scope): description`

**Types:**
- `feat` -- New feature or capability
- `fix` -- Bug fix
- `refactor` -- Code change that neither fixes a bug nor adds a feature
- `docs` -- Documentation only
- `test` -- Adding or updating tests
- `chore` -- Maintenance (dependencies, build config, etc.)
- `meta` -- Changes to `.claude/` files
- `data` -- Generated data and outputs

## Editing Style

**Prefer small, atomic edits.** The auto_allow_edits hook auto-allows edits with <=3 real changes. Split large changes into multiple small edits.

---

# Code Style & Patterns

## Type Safety

- **No bare `except Exception`** -- always catch specific exceptions
- **Every function must specify input and output types**
- **Never use `Any`** -- Use `TypedDict` for dict-like data, `BaseModel` for validated models
- **Never use `# type: ignore`** -- Ask the user how to properly fix type errors
- Use `TypedDict` and Pydantic models for structured data
- Never manually parse agent output -- use structured outputs via Pydantic

### Tool Input Schemas

Define tool inputs as BaseModel classes with `Field(description=...)`. This gives you validation, type-safe access, defaults, and rich JSON Schema generation in one place.

| Do This | Not This |
|---------|----------|
| `class SearchInput(BaseModel): query: str = Field(description="...")` | `{"query": str, "limit": int}` |
| `SearchInput.model_json_schema()` for `@tool` schema | Hand-written dict schemas |
| `SearchInput.model_validate(args)` then `params.query` | `args.get("query", "")` |

## Code as Documentation

The codebase should read as a **monolithic source of truth** -- understandable without any knowledge of its history.

**The test:** Before adding a comment, ask: "Would this comment exist if the code had always been written this way?" If no -- don't add it.

## Error Handling

**MCP tools should:**
- Return `{"content": [...], "is_error": True}` for recoverable errors
- Log exceptions with `logger.exception()` for debugging
- Include actionable error messages

**Agent code should:**
- Raise exceptions for unrecoverable errors
- Use retry decorators for transient failures
- Validate inputs early with Pydantic models

---

# Tooling

## lup-devtools

All development tooling lives in `src/<project>/devtools/` and is exposed as the `lup-devtools` CLI. **Always use `lup-devtools` instead of ad-hoc commands.** Never use `uv run python -c "..."` or bare `python`/`python3`. Use `tmp/*.py` for one-off scripts.

Run `uv run lup-devtools --help` for the full command tree.

## Permission Hooks

Permissions are managed by **PreToolUse hook scripts** in `.claude/plugins/lup/hooks/scripts/`:

| Hook | Tool | Config |
|---|---|---|
| `auto_allow_fetch.py` | WebFetch | `ALLOW_PATTERNS` / `DENY_PATTERNS` (regex) |
| `auto_allow_bash.py` | Bash | `ALLOW_PATTERNS` / `DENY_PATTERNS` (regex) |
| `auto_allow_edits.py` | Edit | Trivial-line counting, protected file list |

**To add a new allowed URL or command**, edit the pattern list at the top of the corresponding hook script.

## Pyright LSP

The `pyright-lsp` plugin provides code intelligence. **Use these actively:**

- **go-to-definition** -- instead of grepping for `def foo`
- **find-references** -- instead of grepping for a symbol name
- **rename-symbol** -- instead of `Edit` with `replace_all`

---

# Process & Communication

## Asking Questions

**Always use the `AskUserQuestion` tool** instead of asking questions in plain text.

## External Resources

When questions involve Claude Code, Agent SDK, or Claude API:
- Use the `claude-code-guide` subagent
- Fetch docs from `https://docs.claude.com/en/agent-sdk/` or `https://docs.claude.com/en/claude-code/`

---

# Self-Improvement Loop

### The Bitter Lesson

When improving the agent, prefer:

| Do This | Not This |
|---------|----------|
| Add tools that provide data | Add prompt rules that constrain behavior |
| Apply general principles | Apply specific pattern patches |
| Provide state/context via tools | Use f-string prompt engineering |
| Create subagents for specialized work | Build complex pipelines in main agent |

### Persistent Agent Pattern

For agents that exist over time, the architecture inverts: the agent is a **persistent presence** that controls its own attention, not a processor steered by an event queue. The agent never ends its turn (Stop hook blocks it). Instead it cycles: wake → read context → think → act → sleep. All timing is tools — sleep, debounce, remind, schedule — so the agent decides when to engage, wait, or come back.

See `src/<project>/lib/realtime.py` for the Scheduler and `src/<project>/agent/tools/realtime.py` for template tools.

### Three Levels of Analysis

1. **Object Level** -- The agent itself: tools, capabilities, behavior
2. **Meta Level** -- The agent's self-tracking: what it monitors about itself
3. **Meta-Meta Level** -- The feedback loop process: scripts, analysis methods

### Running the Feedback Loop

1. **Collect feedback**: `uv run lup-devtools feedback collect`
2. **Read traces deeply**: Don't skip to aggregates. Read 5-10 sessions in detail.
3. **Extract patterns**: Tool failures, capability requests, reasoning quality
4. **Implement changes**: Fix tools -> Build requested capabilities -> Simplify prompts
5. **Update documentation**: This file should evolve with the agent

---

# Anti-Patterns to Avoid

- Adding numeric patches ("subtract 10% from estimates")
- Adding rules the agent can't act on (no access to required data)
- Skipping trace analysis to jump to aggregate statistics
- Over-engineering initial implementations

### Questions to Ask

When proposing changes:
1. Does this add a capability or just a rule?
2. Would this help if the domain changed completely?
3. Are we changing the right level (object/meta/meta-meta)?
4. What data would we need to validate this change worked?
