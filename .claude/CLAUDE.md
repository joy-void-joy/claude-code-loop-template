# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

**Note:** Modifying `CLAUDE.md` means modifying `.claude/CLAUDE.md` (this file).

## Project Overview

This is a **self-improving agent template** built with the Claude Agent SDK. The template provides scaffolding for building agents that can review their own traces and improve over time through a structured feedback loop.

Built with Python 3.13+ and the Claude Agent SDK. Uses `uv` as the package manager.

### Key Concepts

- **Loop Package** (`src/loop/`): The package containing all code for the self-improving agent.
  - **Agent Subpackage** (`src/loop/agent/`): The agent code that the feedback loop improves. Contains core orchestration, tools, subagents, and configuration.
  - **Environment Subpackage** (`src/loop/environment/`): Domain-specific scaffolding (user interaction, game logic, etc.). Evolves with application requirements, but not via the feedback loop.
- **Three-Level Meta Analysis**: Object (agent behavior), Meta (agent self-tracking), Meta-Meta (feedback loop process).

---

# Getting Started

## Reference Files

**Agent (customize for your domain):**
- **src/loop/agent/core.py**: Main agent orchestration
- **src/loop/agent/config.py**: Configuration via pydantic-settings
- **src/loop/agent/models.py**: Output models
- **src/loop/agent/subagents.py**: Subagent definitions
- **src/loop/agent/tool_policy.py**: Conditional tool availability
- **src/loop/agent/tools/example.py**: Example MCP tools

**Library (reusable abstractions):**
- **src/loop/lib/hooks.py**: Hook utilities and composition
- **src/loop/lib/trace.py**: Trace logging, output formatting, color-coded console display
- **src/loop/lib/metrics.py**: Tool call tracking
- **src/loop/lib/scoring.py**: CSV result tracking and score generation

**Top-level:**
- **src/loop/version.py**: Agent version tracking (bump on behavior changes)

**Environment:**
- **src/loop/environment/cli/__main__.py**: Typer CLI with `run` and `loop` (batch + auto-commit) commands

## Commands

```bash
# Install dependencies
uv sync

# Add a new dependency (DO NOT modify pyproject.toml directly)
uv add <package-name>

# Format and lint
uv run ruff format .
uv run ruff check .
uv run pyright

# Run tests
uv run pytest

# Run a single agent session
uv run python -m loop.environment.cli run "your task here"
uv run python -m loop.environment.cli run --session-id my-session "task"

# Run multiple sessions with auto-commit
uv run python -m loop.environment.cli loop "task1" "task2" "task3"
uv run python -m loop.environment.cli loop --no-commit "task1" "task2"

# Commit uncommitted session results
uv run python .claude/plugins/loop/scripts/commit_results.py
uv run python .claude/plugins/loop/scripts/commit_results.py --dry-run

uv run python -m loop.environment.cli --help
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_file.py

# Run tests matching a pattern
uv run pytest -k "test_name"
```

**Test organization:**

- `tests/unit/` - Unit tests (mock external APIs)
- `tests/integration/` - Integration tests (require API keys, use `@pytest.mark.integration`)

## Debugging

**Do not hypothesize -- trace.** When debugging errors, find the actual logs and read the exact exception. Do not list "likely causes" or suggest the user check things. Open the log files yourself, grep for the error, read the traceback, and report what actually happened. If the logs don't contain enough information, say exactly what logging to add and where, so the error is captured next time.

Use `/loop:debug <error message>` to trace an error through the logs automatically.

## Feedback Loop Scripts

```bash
# Collect feedback from sessions
uv run python .claude/plugins/loop/scripts/feedback_collect.py --all-time

# Analyze traces
uv run python .claude/plugins/loop/scripts/trace_analysis.py list
uv run python .claude/plugins/loop/scripts/trace_analysis.py show <session_id>

# Aggregate metrics
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py summary
```

---

# Customization Guide

### Step 1: Run /loop:init

The `/loop:init` command walks you through customizing the template for your domain. It asks about:
- What your agent does
- How outcomes/ground truth are measured
- What metrics matter

### Step 2: Customize Models

Edit `src/loop/agent/models.py`:
- `AgentOutput`: Your agent's structured output format
- `Factor`: Reasoning factors that influence outputs
- `SessionResult`: Complete session data for feedback analysis

### Step 3: Define Subagents

Edit `src/loop/agent/subagents.py`:
- Create specialized subagents for focused tasks
- Define which tools each subagent can use
- Choose appropriate models (cheaper for simple tasks)

### Step 4: Configure Tools

Edit `src/loop/agent/tool_policy.py`:
- Define tool sets that require API keys
- Implement conditional availability logic
- Add MCP server configurations

### Step 5: Customize Scoring

Edit `src/loop/lib/scoring.py`:
- Add domain-specific columns to `CSV_COLUMNS`
- Customize `build_score_row()` for your output format

### Step 6: Set Agent Version

Edit `src/loop/version.py`:
- Set initial `AGENT_VERSION`
- Bump on behavior changes (prompts, tools, subagents)

### Step 5: Update Feedback Collection

Edit `.claude/plugins/loop/scripts/feedback_collect.py`:
- Implement `load_outcomes()` for your domain
- Customize `compute_metrics()` for your metrics
- Add domain-specific summary output

---

# Development Workflow

## Git Workflow

This project uses **git worktrees** (not regular branches) to develop multiple features in parallel.

**IMPORTANT:** Never commit _code_ directly to `main`. Always work in a worktree for code changes.

**Exception:** Data commits (`data(outputs):`) can go directly to main -- generated outputs don't need review.

### Worktrees vs Branches

- **`git checkout -b`**: Creates a branch but stays in the same directory. Switching branches changes all files in place.
- **`git worktree add`**: Creates a new directory with its own working copy. Multiple branches can be worked on simultaneously in separate directories.

### If already in a worktree

**You are typically already in a worktree subbranch.** Check with `git worktree list` to confirm. If you're in a feature worktree, just work directly -- no need to create another worktree or branch out.

### When implementing a feature

1. **Create a worktree** (if the user hasn't already created one):
   ```bash
   git worktree add ./worktrees/feat-name -b feat/feature-name
   cd ./worktrees/feat-name
   ```
2. **Commit regularly and atomically** -- Each commit should represent a single logical change. Don't bundle unrelated changes together.
3. Push the branch when the feature is complete (or periodically for backup)
4. **`/loop:rebase`** -- Creates a clean rebase branch with atomic commits and opens a PR.
5. **Review the PR** -- If changes are needed, fix them on the feature branch and re-run `/loop:rebase` (it force-pushes over the existing rebase branch, updating the PR).
6. **`/loop:close`** -- Once the PR is approved, merges it and cleans up both branches (rebase + original) and remote refs.

### Commit Guidelines

- **Commit before responding** -- Always commit your work before responding to the user. Don't accumulate multiple changes across responses.
- **Commit early, commit often** -- Frequent commits provide checkpoints and make rebasing easier.
- **Keep commits atomic** -- Each commit should do one thing. If you need "and" in your message, it should be two commits.
- **History will be rebased** -- Don't worry about perfect messages during development. The history will be cleaned up before merge.
- **Meaningful final commits** -- After rebasing, each commit should tell a story: what changed and why.

### Commit Message Format

Use conventional commit syntax: `type(scope): description`

**Types:**

- `feat` -- New feature or capability
- `fix` -- Bug fix
- `refactor` -- Code change that neither fixes a bug nor adds a feature
- `docs` -- Documentation only (README, standalone docs)
- `test` -- Adding or updating tests
- `chore` -- Maintenance (dependencies, build config, etc.)
- `meta` -- Changes to `.claude/` files (CLAUDE.md, settings, scripts, commands)
- `data` -- Generated data and outputs

**Examples:**

```
feat(agent): add retry logic for API calls
fix(tools): handle missing API key gracefully
refactor(config): extract settings validation
meta(claude): update commit message guidelines
data(outputs): add session batch results
```

**Note:** The `worktrees/` directory is gitignored.

## Editing Style

**Prefer small, atomic edits.** A PreToolUse hook counts "real" changed lines (ignoring imports, comments, whitespace, blank lines, docstrings) and auto-allows edits with <=3 real changes. Pure deletions, TypedDict/BaseModel definitions, and single-line `replace_all` renames are always auto-allowed.

- **Split large changes into multiple small edits** -- keep real (non-trivial) line changes to <=3 per Edit call
- **Separate concerns** -- move imports in one edit, change logic in another (import changes are trivial and don't count)
- **Use `rename-symbol`** for identifier renames instead of `Edit` with `replace_all`

## Directory Structure

```
src/
└── loop/
    ├── version.py              # Agent version tracking (bump on behavior changes)
    ├── lib/                    # Reusable abstractions (rarely modified)
    │   ├── cache.py            # TTL caching for API responses
    │   ├── history.py          # Session storage/retrieval
    │   ├── hooks.py            # Claude Agent SDK hook utilities
    │   ├── metrics.py          # Tool call tracking (@tracked decorator)
    │   ├── mcp.py              # MCP server creation utilities
    │   ├── notes.py            # RO/RW directory structure
    │   ├── responses.py        # MCP response formatting
    │   ├── retry.py            # Retry decorator with backoff
    │   ├── scoring.py          # CSV result tracking and score generation
    │   └── trace.py            # Trace logging, color-coded console display
    ├── agent/                  # Domain-specific code (feedback loop improves this)
    │   ├── core.py             # Main orchestration
    │   ├── config.py           # Settings via pydantic-settings
    │   ├── models.py           # Output models (customize for your domain)
    │   ├── prompts.py          # System prompt templates
    │   ├── subagents.py        # Subagent definitions
    │   ├── tool_policy.py      # Conditional tool availability
    │   └── tools/
    │       └── example.py      # Example MCP tools (customize)
    └── environment/            # Domain scaffolding (user interaction, game logic)
        └── cli/
            └── __main__.py     # Typer CLI (run + loop with auto-commit)
```

## Code Style & Dependencies

### Primary Libraries

- **claude-agent-sdk**: Primary framework for building agents (use `query()` for one-shot LLM calls with structured output)
- **pydantic**: For data validation and settings
- **pydantic-settings**: For configuration (not dotenv)

### Type Safety Requirements

- **No bare `except Exception`** -- always catch specific exceptions
- **Every function must specify input and output types**
- **Never use `Any`** -- Use `TypedDict` for dict-like data, `BaseModel` for validated models, or specific types. `Any` hides type errors and defeats static analysis.
- **Use Python 3.12+ generics syntax**: `class A[T]`, not `Generic[T]`
- Use `TypedDict` and Pydantic models for structured data
- Never manually parse Claude/agent output -- use structured outputs via Pydantic
- **Never use `# type: ignore`** -- Ask the user how to properly fix type errors
- **Use Pydantic BaseModel instead of dataclasses**

### No Regex/String Parsing for Structured Data

Never use regex or string substitution to parse HTML, XML, JSON, or other structured formats. Use proper parsing libraries:

- **Web page text extraction**: Use `trafilatura` -- it handles boilerplate removal, content extraction, and metadata
- **HTML DOM manipulation**: Use `beautifulsoup4` when you need to navigate/query the DOM tree
- **XML**: Use `xml.etree.ElementTree` or `lxml`
- **JSON embedded in HTML**: Parse the HTML with BeautifulSoup first, then `json.loads()`

### Use Standard Libraries

When integrating with external services (APIs, data sources, etc.):

- **Use existing Python libraries first** -- Check PyPI for official or well-maintained client libraries before writing raw HTTP requests
- **Don't rebuild the wheel** -- If a library exists with good documentation and maintenance, use it

### Code as Documentation

The codebase should read as a **monolithic source of truth** -- understandable without any knowledge of its history.

**The test:** Before adding a comment, ask: "Would this comment exist if the code had always been written this way?" If no -- don't add it.

**Do not:**

- Add comments to explain modifications you made
- Reference what code used to do (e.g., "Previously this returned None")
- Add inline comments when changing a line
- Use phrases like "now", "new", "updated", "fixed", or "changed" in comments

**Do:**

- Write comments that would make sense to someone who never saw previous versions
- Use commit messages for change history, not code comments
- Only add comments that document genuinely non-obvious behavior

### Error Handling Philosophy

**MCP tools should:**

- Return `{"content": [...], "is_error": True}` for recoverable errors
- Log exceptions with `logger.exception()` for debugging
- Include actionable error messages (what failed, why, what to try)

**Agent code should:**

- Raise exceptions for unrecoverable errors (missing config, invalid state)
- Use the `with_retry` decorator for transient failures (HTTP timeouts, rate limits)
- Validate inputs early with Pydantic models

**Never silently swallow errors** -- either handle them meaningfully or let them propagate.

### DRY: Don't Repeat Yourself

- **Never duplicate code** -- If logic exists in `lib/`, import it. Don't copy-paste.
- **Utilities belong in `lib/`** -- Functions like `print_block`, `TraceLogger`, formatters go in lib, not agent.
- **`agent/` imports from `lib/`** -- The agent layer uses lib abstractions, never redefines them.
- **Check before writing** -- Before creating a utility, search lib/ for existing implementations.

### Tools

- **uv**: Package manager. Use `uv add <package>` (never edit pyproject.toml directly)
- **ruff**: Formatting and linting
- **pyright**: Type checking

### Pyright LSP

The `pyright-lsp` plugin is enabled and provides code intelligence tools. **Use these actively** -- they are faster and more accurate than grep-based searches for code understanding and refactoring.

**Navigation (use before editing unfamiliar code):**

- **go-to-definition** -- Jump to where a symbol is defined. Use this instead of grepping for `def foo` or `class Foo`.
- **find-references** -- Find all usages of a symbol. Use this instead of grepping for a symbol name.
- **hover-documentation** -- Get type info and docs for a symbol at a position.
- **list-symbols** -- List all symbols in a file. Use this instead of grepping for `def ` or `class `.
- **find-implementations** -- Find implementations of an interface or abstract method.
- **trace-call-hierarchy** -- Understand call chains. Use this instead of manually tracing function calls.

**Refactoring:**

- **rename-symbol** -- Rename a symbol across the workspace. **Always prefer this over `Edit` with `replace_all`** for identifier renames -- it understands scope and won't rename unrelated identifiers.

**Diagnostics:**

- After every file edit, pyright automatically analyzes changes and reports type errors. Pay attention to these -- they catch issues immediately.

**When to use LSP vs grep/Edit:**

| Task | Use LSP | Use grep/Edit |
|---|---|---|
| Find where a function is defined | `go-to-definition` | |
| Find all callers of a function | `find-references` | |
| Rename a variable/function/class | `rename-symbol` | |
| Search for a string literal | | `Grep` |
| Search across non-Python files | | `Grep` |
| Change logic within a function | | `Edit` |
| Add new code | | `Edit` / `Write` |

---

# Tooling

## Helper Scripts

The `.claude/plugins/loop/scripts/` directory contains reusable scripts. **Always use these scripts instead of ad-hoc commands.** Never use `uv run python -c "..."` or bare `python`/`python3` -- these are denied by the Bash permission hook.

If you find yourself running the same command repeatedly, **create a script** in `.claude/plugins/loop/scripts/` and document it here.

**Write scripts in Python using [typer](https://typer.tiangolo.com/)** for CLI interfaces. Use **[sh](https://sh.readthedocs.io/)** for shell commands instead of `subprocess`.

### inspect_api.py

Explore package APIs -- never use `python -c "import ..."` or ad-hoc REPL commands.

```bash
uv run python .claude/plugins/loop/scripts/inspect_api.py <module.Class>
uv run python .claude/plugins/loop/scripts/inspect_api.py <module.Class.method>
uv run python .claude/plugins/loop/scripts/inspect_api.py <module.Class> --help-full
```

### module_info.py

Get paths and source code for installed Python modules.

```bash
uv run python .claude/plugins/loop/scripts/module_info.py path <module>
uv run python .claude/plugins/loop/scripts/module_info.py source <module> [--lines N]
```

### new_worktree.py

Create a new git worktree with setup.

```bash
uv run python .claude/plugins/loop/scripts/new_worktree.py <name> [--no-sync] [--no-copy-data]
```

Creates worktree, copies `.env.local` and data directories, runs `uv sync`.

### commit_results.py

Commit uncommitted session results (one commit per session).

```bash
uv run python .claude/plugins/loop/scripts/commit_results.py
uv run python .claude/plugins/loop/scripts/commit_results.py --dry-run
```

## Permission Hooks

Permissions are managed by **PreToolUse hook scripts** in `.claude/plugins/loop/hooks/scripts/` rather than glob patterns in `settings.json`. Each hook uses regex patterns for precise control.

| Hook | Tool | Config |
|---|---|---|
| `auto_allow_fetch.py` | WebFetch | `ALLOW_PATTERNS` (regex), `DENY_PATTERNS` (regex + reason) |
| `auto_allow_bash.py` | Bash | `ALLOW_PATTERNS` (regex), `DENY_PATTERNS` (regex + reason) |
| `auto_allow_edits.py` | Edit | Trivial-line counting, protected file list |
| `pre_push_check.py` | Bash (git push) | Runs pyright, ruff, pytest before push |
| `check_plan_md.py` | Bash (git push) | Warns if PLAN.md missing on feature branches |
| `protect_tests.py` | Edit\|Write | TDD mode test protection |

**To add a new allowed URL or command**, edit the pattern list at the top of the corresponding hook script. Non-matching inputs fall through to the user prompt (ask).

`settings.json` only contains rules that don't need regex: `WebSearch` (allow), `Read(.local)` (deny), `Edit(pyproject.toml)` (ask).

## Settings & Configuration

All Claude Code settings modifications should be **project-level** (in `.claude/settings.json`), not user-level.

---

# Process & Communication

## Asking Questions

**Always use the `AskUserQuestion` tool** instead of asking questions in plain text. This applies to:

- Clarifying requirements or ambiguous instructions
- Offering choices between implementation approaches
- Confirming before destructive or irreversible actions
- Proposing changes or improvements
- Any situation where you need user input before proceeding

Even for open-ended questions, use `AskUserQuestion` with options that include a custom input option. This allows structured notification parsing.

**When proposing changes:**

- **Propose, don't assume**: Use AskUserQuestion before making changes
- **Show context**: Show relevant current state before proposing
- **Explain rationale**: Every suggestion should include why it would help
- **Offer alternatives**: Present options when multiple valid approaches exist

**When in doubt, ask.** Err on the side of asking questions rather than making assumptions.

## Planning & Documentation

**PLAN.md** is the source of truth for what has been built and what remains. Keep it synchronized with reality:

- **Reflect actual state**: PLAN.md must describe what exists, not aspirational designs
- Mark completed items when finishing work (`[x]`)
- Update architecture decisions as they evolve
- Add new tasks discovered during implementation
- Keep status indicators current (`[ ]` pending, `[x]` done, `[~]` in progress)
- **No speculative code**: Describe what to build, not how

## Slash Commands & Skills

**After every command invocation**, reflect on how it was actually used vs. documented:

1. **Compare intent vs usage**: Did the command serve its documented purpose, or was it adapted?
2. **Notice patterns**: When the user corrects your approach or redirects focus, that's a signal the command should evolve.
3. **Proactively propose updates**: Use AskUserQuestion to suggest command improvements.

**Evolution signals:**

- User provides external docs -> Add doc-fetching or reference to command
- User corrects your approach -> Update command to prevent future errors
- User asks for something the command should cover -> Expand scope
- User ignores sections -> Consider simplifying

## External Resources

When questions involve Claude Code, Agent SDK, or Claude API:

1. **Use the claude-code-guide subagent**:
   ```
   Task(subagent_type="claude-code-guide", prompt="<specific question>")
   ```

2. **Fetch docs directly** for specific pages:
   - `WebFetch(url="https://docs.claude.com/en/agent-sdk/<topic>")`
   - `WebFetch(url="https://docs.claude.com/en/claude-code/<topic>")`

When the user provides documentation links, incorporate that knowledge into CLAUDE.md or relevant commands.

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

### Three Levels of Analysis

1. **Object Level** -- The agent itself: tools, capabilities, behavior
2. **Meta Level** -- The agent's self-tracking: what it monitors about itself
3. **Meta-Meta Level** -- The feedback loop process: scripts, analysis methods

### Running the Feedback Loop

1. **Collect feedback**: `uv run python .claude/plugins/loop/scripts/feedback_collect.py`
2. **Read traces deeply**: Don't skip to aggregates. Read 5-10 sessions in detail.
3. **Extract patterns**: Tool failures, capability requests, reasoning quality
4. **Implement changes**: Fix tools -> Build requested capabilities -> Simplify prompts
5. **Update documentation**: This file should evolve with the agent

### What to Track Per Session

- **Outputs**: Final results saved to `notes/sessions/<session_id>/`
- **Traces**: Reasoning logs saved to `notes/traces/<session_id>/`
- **Scores**: Unified CSV at `notes/scores.csv` (appended per session, includes agent version)
- **Metrics**: Tool calls, timing, errors via metrics tracking

---

# Configuration

### Environment Variables

The `.env` file contains the template configuration. Create `.env.local` for your secrets (gitignored):

```bash
# .env.local - your secrets
ANTHROPIC_API_KEY=your-key

# Optional overrides
# AGENT_MODEL=claude-sonnet-4-20250514
# AGENT_MAX_BUDGET_USD=5.00
```

Settings in `.env.local` override `.env`.

### Settings

Configuration is loaded via pydantic-settings. See `src/loop/agent/config.py` for all options.

---

# Anti-Patterns to Avoid

- Adding numeric patches ("subtract 10% from estimates")
- Adding rules the agent can't act on (no access to required data)
- Skipping trace analysis to jump to aggregate statistics
- Over-engineering initial implementations
- Making changes in `loop.environment` when `loop.agent` is the right place

### Questions to Ask

When proposing changes:
1. Does this add a capability or just a rule?
2. Would this help if the domain changed completely?
3. Are we changing the right level (object/meta/meta-meta)?
4. What data would we need to validate this change worked?
