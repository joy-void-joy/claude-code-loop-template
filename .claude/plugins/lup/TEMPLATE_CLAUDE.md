# CLAUDE.md Template

This is the portable CLAUDE.md scaffold that lup installs into downstream projects. It contains conventions, workflow patterns, and coding standards that apply to any project using lup.

**How it's used:** `/lup:init` and `/lup:install` perform a **section-level merge** — they compare this template's sections against the target's existing CLAUDE.md, add sections that are missing, and leave existing sections untouched. Placeholders like `<project>` are replaced with the actual project name.

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

### The Bitter Lesson

The single most important principle for improving this agent: **give it more tools and capabilities, not more rules.**

| Do This                                               | Not This                                           |
| ----------------------------------------------------- | -------------------------------------------------- |
| Add tools that provide data                           | Add prompt rules that constrain behavior           |
| Apply general principles                              | Apply specific pattern patches                     |
| Communicate principles and the _why_                  | Prescribe rigid mechanical procedures              |
| Provide state/context via tools                       | Use f-string prompt engineering                    |
| Set `model=opus 4.6`, `max_thinking_tokens=128_000-1` | Compensate for weak reasoning with complex prompts |
| See what went wrong from first principles             | Make small edits to patch one mistake              |
| Create subagents for specialized work                 | Build complex pipelines in main agent              |

**Tools are the primary scaffold.** When the agent struggles, the answer is almost always a missing tool — not a missing prompt paragraph. A tool that returns the right data at the right time is worth more than any amount of prompt engineering.

**The test:** Does this change add a capability, or just a rule? Would it still help if the domain changed completely? If not, it's over-fitted.

### Tool Design Philosophy

Tools are the interface between the agent and its environment. They outlast any particular prompt revision, and they compose — each new tool multiplies the agent's options rather than constraining them.

**Prompts rot; tools don't.** Tool names and sets change as the agent evolves. If the prompt lists them, every addition or rename means updating two places that can drift apart. Letting the agent discover tools through their descriptions keeps the prompt focused on _what to do_ and _how to reason_ — things that stay stable.

**The tool description is the contract.** It's the only documentation the agent sees for a tool. When the agent misuses a tool or ignores one it should use, the description is usually the problem. A good description answers:

1. **What** — What does this tool do? (concrete behavior, not vague summary)
2. **When** — When should the agent reach for this tool? (triggers, conditions)
3. **Why** — Why does this tool exist? (what problem it solves, what gap it fills)

Compare: `"Search the web for information"` vs. `"Search the web using keyword queries. Use this when the agent needs current information not available in local data, or when verifying claims against external sources. Exists because the agent has no built-in knowledge of events after its training cutoff. Returns a list of {title, url, snippet} results ordered by relevance."`

The first leaves the agent guessing about when and why. The second makes the tool self-selecting — the agent can match its situation to the description without prompt-level instructions.

### Persistent Agent Pattern

For agents that exist over time — maintaining conversations, monitoring systems, playing games, running autonomous workflows — the architecture inverts: the agent is a **persistent presence** that controls its own attention, not a processor steered by an event queue.

| Do This                                                     | Not This                                    |
| ----------------------------------------------------------- | ------------------------------------------- |
| Agent sleeps when it chooses, wakes on events               | Event queue drives agent responses          |
| All timing is tools (sleep, debounce, remind, schedule)     | Hardcode delays or polling in orchestration |
| Stop hook prevents turn from ending — only sleep yields     | Request-response per event                  |
| Pull-based state reading (agent calls `context` when ready) | Push state changes as SDK user turns        |
| Agent parks thoughts (ideas, reminders) for later           | Drop context between interactions           |
| Expose environment state as tool-readable data              | Hide activity from the agent                |

**The core loop:** The agent never ends its turn. A Stop hook blocks it. Instead it cycles: wake → read context → think → act → meta-assess → sleep. The only way to yield control is `sleep()`, which blocks on an asyncio Event until something wakes it (external event, timer, reminder). This keeps the agent centered — it decides when to engage, when to wait, and when to come back.

**Why not an event queue?** A queue steers the agent by its inputs — every event forces a reaction. The sleep/wake pattern lets the agent stay centered. It can debounce event bursts, schedule actions, set reminders, and park thoughts for later — all on its own terms. The agent continues thinking across sleep cycles rather than starting fresh on each event.

**Library support:** `src/<project>/lib/realtime.py` provides the `Scheduler` class (sleep/wake, debounce, scheduled actions, reminders, delayed actions) and hook factories (`create_stop_guard`, `create_pending_event_guard`). See the example tools in `src/<project>/agent/tools/realtime.py`.

### Reflection Pattern

Agents produce better output when forced to self-assess before committing. The reflection pattern has three components:

1. **Reflection tool** (`agent/tools/reflect.py`): A domain-customizable tool the agent calls to record its self-assessment — confidence, key uncertainties, tool audit, process reflection. Optionally runs an independent reviewer sub-agent.
2. **Reflection gate** (`lib/reflect.py`): A `ReflectionGate` flag tracker + `create_reflection_gate()` hook factory. Denies a target tool until the agent has reflected.
3. **Wiring**: The gate blocks `StructuredOutput` (one-shot agents) or `sleep` (persistent agents) until reflection occurs.

**Customizing reflection:** The gate mechanism in `lib/reflect.py` is domain-neutral and parametric. The reflection _tool_ and its input model (`ReflectInput` in `agent/tools/reflect.py`) are domain-specific — add fields for your domain (e.g., factor analysis for forecasting, move evaluation for games). The reviewer prompt should target your domain's common failure modes.

**When to skip the reviewer:** Set `skip_reviewer=True` for speed-sensitive or trivial tasks. The reviewer adds latency (separate Sonnet call with tool access) but catches calibration errors and reasoning gaps.

---

# Getting Started

## Reference Files

**Agent (customize for your domain):**

- **src/<project>/agent/core.py**: Main agent orchestration
- **src/<project>/agent/config.py**: Configuration via pydantic-settings
- **src/<project>/agent/models.py**: Output models
- **src/<project>/agent/subagents.py**: Subagent definitions
- **src/<project>/agent/tool_policy.py**: Conditional tool availability
- **src/<project>/agent/tools/example.py**: Example MCP tools
- **src/<project>/agent/tools/reflect.py**: Forced self-review tool with optional reviewer sub-agent

**Library (reusable abstractions):**

- **src/<project>/lib/hooks.py**: Hook utilities and composition
- **src/<project>/lib/paths.py**: Centralized version-aware path constants and helpers
- **src/<project>/lib/trace.py**: Trace logging, output formatting, color-coded console display
- **src/<project>/lib/metrics.py**: Tool call tracking
- **src/<project>/lib/realtime.py**: Scheduler for persistent agents (sleep/wake, debounce, reminders)
- **src/<project>/lib/client.py**: Centralized Agent SDK client (build_client, run_query, one_shot)
- **src/<project>/lib/reflect.py**: Reflection gate (enforce reflect-before-output)
- **src/<project>/lib/throttle.py**: Rate limiting (concurrency + interval)

**Top-level:**

- **src/<project>/version.py**: Agent version tracking (bump on behavior changes)

**Environment:**

- **src/<project>/environment/cli/\_\_main\_\_.py**: Typer CLI with `run` and `loop` (batch + auto-commit) commands

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
uv run python -m <project>.environment.cli run "your task here"
uv run python -m <project>.environment.cli run --session-id my-session "task"

# Run multiple sessions with auto-commit
uv run python -m <project>.environment.cli loop "task1" "task2" "task3"
uv run python -m <project>.environment.cli loop --no-commit "task1" "task2"

# Commit uncommitted session results
uv run lup-devtools git commit-results
uv run lup-devtools git commit-results --dry-run

uv run python -m <project>.environment.cli --help
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

Use `/lup:debug <error message>` to trace an error through the logs automatically.

## Feedback Loop Scripts

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

# Customization Guide

### Step 1: Run /lup:init

The `/lup:init` command walks you through customizing the template for your domain. It asks about:

- What your agent does
- How outcomes/ground truth are measured
- What metrics matter

### Step 2: Customize Models

Edit `src/<project>/agent/models.py`:

- `AgentOutput`: Your agent's structured output format
- `Factor`: Reasoning factors that influence outputs
- `SessionResult`: Complete session data for feedback analysis

### Step 3: Define Subagents

Edit `src/<project>/agent/subagents.py`:

- Create specialized subagents for focused tasks
- Define which tools each subagent can use
- Choose appropriate models (cheaper for simple tasks)

### Step 4: Configure Tools

Edit `src/<project>/agent/tool_policy.py`:

- Define tool sets that require API keys
- Implement conditional availability logic
- Add MCP server configurations

### Step 5: Configure Reflection

Edit `src/<project>/agent/tools/reflect.py`:

- Customize `ReflectInput` fields for your domain (e.g., factor analysis for forecasting)
- Customize the reviewer system prompt for your domain's failure modes
- Decide whether the reviewer sub-agent adds value (adds latency but catches errors)
- The gate in `core.py` is already wired — reflection is enforced by default

### Step 6: Set Agent Version

Edit `src/<project>/version.py`:

- Set initial `AGENT_VERSION`
- Bump on behavior changes (prompts, tools, subagents)

### Step 7: Enable Persistent Agent Mode (Optional)

For agents that exist over time (conversations, monitoring, games), use the persistent agent pattern:

- Wire `Scheduler` from `lib/realtime.py` into your session
- Add Stop hook to prevent turn ending (`create_stop_guard`)
- Implement sleep/context/reply tools from `agent/tools/realtime.py`
- Replace the request-response `run_agent()` in `core.py` with a sleep/wake loop
- The reflection gate also works here — gate `sleep` instead of `StructuredOutput`

### Step 8: Update Feedback Collection

Edit `src/<project>/devtools/feedback.py`:

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
4. **`/lup:rebase`** -- Pushes the branch, opens a PR, then cleans up the commit history with `git reset --soft main` and force-pushes.
5. **Review the PR** -- If changes are needed, fix them on the feature branch and re-run `/lup:rebase` (it rebuilds the history and force-pushes, updating the PR).
6. **`/lup:close`** -- Once the PR is approved, merges it and cleans up the branch.

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

## Editing Style

**Prefer small, atomic edits.** A PreToolUse hook counts "real" changed lines (ignoring imports, comments, whitespace, blank lines, docstrings) and auto-allows edits with <=3 real changes. Pure deletions, TypedDict/BaseModel definitions, and single-line `replace_all` renames are always auto-allowed.

- **Split large changes into multiple small edits** -- keep real (non-trivial) line changes to <=3 per Edit call
- **Separate concerns** -- move imports in one edit, change logic in another (import changes are trivial and don't count)
- **Use `rename-symbol`** for identifier renames instead of `Edit` with `replace_all`

## Directory Structure

```
src/
└── <project>/
    ├── version.py              # Agent version tracking (bump on behavior changes)
    ├── lib/                    # Reusable abstractions (rarely modified)
    │   ├── client.py           # Agent SDK client (build_client, run_query, one_shot)
    │   ├── hooks.py            # Claude Agent SDK hook utilities
    │   ├── metrics.py          # Tool call tracking (@tracked decorator)
    │   ├── mcp.py              # MCP server creation utilities
    │   ├── paths.py            # Centralized version-aware path constants and helpers
    │   ├── realtime.py         # Scheduler for persistent agents (sleep/wake, debounce)
    │   ├── reflect.py          # Reflection gate (enforce reflect-before-output)
    │   ├── responses.py        # MCP response formatting
    │   ├── retry.py            # Retry decorator with backoff
    │   ├── throttle.py         # Rate limiting (concurrency + interval)
    │   └── trace.py            # Trace logging, color-coded console display
    ├── agent/                  # Domain-specific code (feedback loop improves this)
    │   ├── core.py             # Main orchestration
    │   ├── config.py           # Settings via pydantic-settings
    │   ├── models.py           # Output models (customize for your domain)
    │   ├── prompts.py          # System prompt templates
    │   ├── subagents.py        # Subagent definitions
    │   ├── tool_policy.py      # Conditional tool availability
    │   └── tools/
    │       ├── example.py      # Example MCP tools (customize)
    │       ├── realtime.py     # Real-time tools template (sleep, context, reply)
    │       └── reflect.py      # Forced self-review tool (reviewer sub-agent)
    ├── devtools/               # Development CLI (lup-devtools entry point)
    │   ├── main.py             # Root Typer app composing sub-apps
    │   ├── feedback.py         # Feedback collection
    │   ├── trace.py            # Trace analysis
    │   └── metrics.py          # Aggregate metrics
    └── environment/            # Domain scaffolding (user interaction, game logic)
        └── cli/
            └── __main__.py     # Typer CLI (run + loop with auto-commit)
```

---

# Code Style & Dependencies

## Primary Libraries

- **claude-agent-sdk**: Primary framework for building agents (use `query()` for one-shot LLM calls with structured output)
- **pydantic**: For data validation and settings
- **pydantic-settings**: For configuration (not dotenv)

## Type Safety Requirements

- **No bare `except Exception`** -- always catch specific exceptions
- **Every function must specify input and output types**
- **Never use `Any`, `dict[str, Any]`, or `dict[str, object]`** -- Use `TypedDict` for dict-like data, `BaseModel` for validated models, or specific types. These erase type information and defeat static analysis.
  - **MCP tool inputs**: The SDK types `@tool` handler args as `dict[str, Any]`. Always `BaseModel.model_validate(args)` immediately — don't pass around the raw dict.
  - **MCP tool outputs**: Define a `TypedDict` for the return dict (the SDK types it as `dict[str, Any]` but we use our own typed wrapper).
  - **SDK hooks**: Return `SyncHookJSONOutput` (TypedDict from `claude_agent_sdk.types`) — don't hand-build `dict[str, Any]`. Use the typed hook inputs (`PreToolUseHookInput`, etc.) and specific output types (`PreToolUseHookSpecificOutput`, etc.).
  - **SDK types to prefer**: Use the SDK's own typed classes instead of raw dicts — `HookMatcher`, `AgentDefinition`, `ClaudeAgentOptions`, `McpServerConfig`, `PermissionResultAllow`/`Deny`, `ContentBlock`, `Message`, `TextBlock`, `ToolUseBlock`, `ToolResultBlock`. Import from top-level `claude_agent_sdk` when available; `SyncHookJSONOutput`, `HookEvent`, and hook-specific output types require `claude_agent_sdk.types`.
- **Use Python 3.12+ generics syntax**: `class A[T]`, not `Generic[T]`
- Use `TypedDict` and Pydantic models for structured data
- Never manually parse Claude/agent output -- use structured outputs via Pydantic
- **Never use `# type: ignore`** -- Ask the user how to properly fix type errors
- **Use Pydantic BaseModel instead of dataclasses**
- **Use `match`/`case` instead of `if`/`elif` chains** for dispatching on values or ranges

## Tool Input Schemas

Define tool inputs as BaseModel classes with `Field(description=...)`. This gives you validation, type-safe access, defaults, and rich JSON Schema generation in one place.

| Do This                                                               | Not This                       |
| --------------------------------------------------------------------- | ------------------------------ |
| `class SearchInput(BaseModel): query: str = Field(description="...")` | `{"query": str, "limit": int}` |
| `SearchInput.model_json_schema()` for `@tool` schema                  | Hand-written dict schemas      |
| `SearchInput.model_validate(args)` then `params.query`                | `args.get("query", "")`        |

## No String Manipulation on Structured Data

If you're reaching for `re`, `.replace()`, `.split()`, string slicing, or any string operation to extract, transform, or filter structured data, something is wrong. Operate on the structure directly.

- **Web pages**: Use `trafilatura` for text extraction, `beautifulsoup4` for DOM queries
- **XML**: Use `xml.etree.ElementTree` or `lxml`
- **JSON**: `json.loads()`, not regex
- **SDK objects**: Filter `ContentBlock` lists by type and attribute (e.g. `ToolUseBlock.name`, `ToolResultBlock.tool_use_id`)
- **Dates/timestamps**: Parse to `datetime`, don't compare strings
- **URLs**: Use `urllib.parse`, not string splitting
- **File paths**: Use `pathlib.Path`, not string concatenation

String operations are for formatting output. If you're using them to understand or transform data, you're working at the wrong abstraction level. `import re` in particular is a code smell -- if you find yourself writing a regex, stop and look for the structured API.

## Use Standard Libraries

When integrating with external services (APIs, data sources, etc.):

- **Use existing Python libraries first** -- Check PyPI for official or well-maintained client libraries before writing raw HTTP requests
- **Don't rebuild the wheel** -- If a library exists with good documentation and maintenance, use it

## Code as Documentation

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

## Error Handling Philosophy

**MCP tools should:**

- Return `{"content": [...], "is_error": True}` for recoverable errors
- Log exceptions with `logger.exception()` for debugging
- Include actionable error messages (what failed, why, what to try)

**Agent code should:**

- Raise exceptions for unrecoverable errors (missing config, invalid state)
- Use the `with_retry` decorator for transient failures (HTTP timeouts, rate limits)
- Validate inputs early with Pydantic models

**Never silently swallow errors** -- either handle them meaningfully or let them propagate.

## DRY: Don't Repeat Yourself

- **Never duplicate code** -- If logic exists in `lib/`, import it. Don't copy-paste.
- **Utilities belong in `lib/`** -- Functions like `print_block`, `TraceLogger`, formatters go in lib, not agent.
- **`agent/` imports from `lib/`** -- The agent layer uses lib abstractions, never redefines them.
- **Check before writing** -- Before creating a utility, search lib/ for existing implementations.
- **Placement test** -- Can this module be used as-is without templating or source modification? If yes, it belongs in `lib/`, not `agent/`. Quick proxy: does it import from `agent/`?

## Parametric Library Design

Files in `src/<project>/lib/` must be **complete-as-is and configurable through function arguments** — never by modifying the source. Domain-specific code belongs in `agent/`. If a lib module requires subclassing or source modification to customize, it violates this principle.

- **Use function parameters** for customization (callbacks, config objects, path overrides)
- **Use `configure()`-style functions** for module-level state that needs overriding
- **No imports from `agent/`** in lib code — the dependency arrow points one way

## Tools

- **uv**: Package manager. Use `uv add <package>` (never edit pyproject.toml directly)
- **ruff**: Formatting and linting
- **pyright**: Type checking

## Pyright LSP

The `pyright-lsp` plugin provides code intelligence. **Use these actively** -- they are faster and more accurate than grep-based searches for code understanding and refactoring.

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

| Task                             | Use LSP            | Use grep/Edit    |
| -------------------------------- | ------------------ | ---------------- |
| Find where a function is defined | `go-to-definition` |                  |
| Find all callers of a function   | `find-references`  |                  |
| Rename a variable/function/class | `rename-symbol`    |                  |
| Search for a string literal      |                    | `Grep`           |
| Search across non-Python files   |                    | `Grep`           |
| Change logic within a function   |                    | `Edit`           |
| Add new code                     |                    | `Edit` / `Write` |

---

# Tooling

## lup-devtools

All development tooling lives in `src/<project>/devtools/` and is exposed as the `lup-devtools` CLI entry point. **Always use `lup-devtools` instead of ad-hoc commands.** Never use `uv run python -c "..."` or bare `python`/`python3` -- these are denied by the Bash permission hook.

If you find yourself running the same command repeatedly, **add a command** to `src/<project>/devtools/` and document it here. Use `tmp/*.py` for one-off scripts.

**Write scripts in Python using [typer](https://typer.tiangolo.com/)** for CLI interfaces. Use **[sh](https://sh.readthedocs.io/)** for shell commands instead of `subprocess`.

Run `uv run lup-devtools --help` for the full command tree.

## Permission Hooks

Permissions are managed by **PreToolUse hook scripts** in `.claude/plugins/lup/hooks/scripts/` rather than glob patterns in `settings.json`. Each hook uses regex patterns for precise control.

| Hook                  | Tool     | Config                                                            |
| --------------------- | -------- | ----------------------------------------------------------------- |
| `auto_allow_fetch.py` | WebFetch | `ALLOW_PATTERNS` (regex), `DENY_PATTERNS` (regex + reason)        |
| `auto_allow_bash.py`  | Bash     | `RULES` list of `Allow`/`Deny` (last-match-wins, like .gitignore) |
| `auto_allow_edits.py` | Edit     | Trivial-line counting, protected file list                        |

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

See [The Bitter Lesson](#the-bitter-lesson) and [Tool Design Philosophy](#tool-design-philosophy) above — these are the governing principles for all agent improvements.

**When analyzing failures:** Ask "what general principle would have prevented this?" not "what specific rule would catch this case?" If the agent made one bad decision, the fix is almost never a prompt line about that specific decision. Instead: does the agent have enough context? Does it have the right tools? Is the model strong enough?

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

### What to Track Per Session

- **Sessions**: Results saved to `notes/traces/<version>/sessions/<session_id>/`
- **Outputs**: Task outputs saved to `notes/traces/<version>/outputs/<task_id>/`
- **Traces**: Reasoning logs saved to `notes/traces/<version>/logs/<session_id>/`
- **Metrics**: Tool calls, timing, errors via metrics tracking

---

# Configuration

### Environment Variables

The `.env` file contains the template configuration. Create `.env.local` for your secrets (gitignored):

```bash
# .env.local - your secrets (ANTHROPIC_API_KEY is read directly by the SDK from env)

# Optional overrides
# AGENT_MODEL=claude-sonnet-4-20250514
# AGENT_MAX_BUDGET_USD=5.00
```

Settings in `.env.local` override `.env`.

### Settings

Configuration is loaded via pydantic-settings. See `src/<project>/agent/config.py` for all options.

---

# Anti-Patterns to Avoid

- Adding numeric patches ("subtract 10% from estimates")
- Prompting the agent with rigid mechanical procedures instead of guidelines and rationale
- Adding absolute thresholds ("if X happens N times, do Y")
- Adding rules the agent can't act on (no access to required data)
- Making small edits to patch one mistake instead of finding the general cause
- Listing tools by name in the system prompt (creates two sources of truth that drift apart)
- Writing terse tool descriptions (the agent can't use a tool well if it doesn't know when or why)
- Skipping trace analysis to jump to aggregate statistics
- Over-engineering initial implementations

### Questions to Ask

When proposing changes:

1. Does this add a capability or just a rule?
2. Would this help if the domain changed completely?
3. Are we changing the right level (object/meta/meta-meta)?
4. What general principle would have prevented this failure?
5. What data would we need to validate this change worked?
