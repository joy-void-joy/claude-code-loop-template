# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

**Note:** Modifying `CLAUDE.md` means modifying `.claude/CLAUDE.md` (this file).

## Project Overview

This is a **self-improving agent template and scaffold** built with the Claude Agent SDK. It serves two roles:

1. **Template** — Code that downstream projects customize for their domain: agent prompts, tools, models, environment scaffolding. `/lup:brainstorm` explores the design, `/lup:init` executes the customization.
2. **Scaffold** — Agents, commands, hooks, and workflows that downstream projects inherit and extend. These provide the development workflow (commit, rebase, feedback loop) and analysis infrastructure (trace exploration, version comparison) that every project needs.

When reviewing changes from downstream repos (`/lup:update`), the goal is to **generalize domain-specific patterns back into the template**. The bias is toward inclusion: if a pattern emerged from real use, it likely belongs in the template.

Built with Python 3.13+ and the Claude Agent SDK. Uses `uv` as the package manager.

### Naming

- **Claude** = the meta-agent (Claude Code) that modifies the codebase, runs commands, and manages the development workflow
- **Lup** = the SDK agent inside the code being built and improved — the agent that runs via the CLI and produces outputs

### Key Concepts

- **Lup Package** (`src/lup/`): All code for the self-improving agent.
  - **Agent** (`src/lup/agent/`): The agent code that the feedback loop improves. Contains core orchestration, tools, subagents, and configuration.
  - **Environment** (`src/lup/environment/`): Domain-specific scaffolding (user interaction, game logic, etc.). Evolves with application requirements, but not via the feedback loop.
- **Three-Level Meta Analysis**: Object (agent behavior), Meta (agent self-tracking), Meta-Meta (feedback loop process).

---

## Principles

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

**Tools are the primary scaffold.** When the agent struggles, the answer is almost always a missing tool — not a missing prompt paragraph.

**The test:** Does this change add a capability, or just a rule? Would it still help if the domain changed completely? If not, it's over-fitted.

### Tool Design Philosophy

Tools outlast any particular prompt revision, and they compose — each new tool multiplies the agent's options rather than constraining them.

**Prompts rot; tools don't.** If the prompt lists tool names, every addition or rename means updating two places that can drift apart. Let the agent discover tools through their descriptions.

**The tool description is the contract.** A good description answers:

1. **What** — What does this tool do? (concrete behavior, not vague summary)
2. **When** — When should the agent reach for this tool? (triggers, conditions)
3. **Why** — Why does this tool exist? (what problem it solves, what gap it fills)

Compare: `"Search the web for information"` vs. `"Search the web using keyword queries. Use this when the agent needs current information not available in local data, or when verifying claims against external sources. Returns a list of {title, url, snippet} results ordered by relevance."`

---

## Architecture

### Directory Structure

```
src/
└── lup/
    ├── version.py              # Agent version tracking (bump on behavior changes)
    ├── lib/                    # Reusable abstractions (rarely modified)
    │   ├── client.py           # Agent SDK client (build_client, run_query, one_shot)
    │   ├── cache.py            # TTL caching for API responses
    │   ├── history.py          # Session storage/retrieval
    │   ├── hooks.py            # Claude Agent SDK hook utilities
    │   ├── metrics.py          # Tool call tracking (@tracked decorator)
    │   ├── mcp.py              # MCP server creation utilities
    │   ├── notes.py            # RO/RW directory structure
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
    │   ├── agent.py            # Agent introspection and debugging
    │   ├── api.py              # API inspection and module info
    │   ├── dev.py              # Worktree management
    │   ├── git.py              # Session commit operations
    │   ├── sync.py             # Upstream sync tracking
    │   ├── usage.py            # Claude Code usage display
    │   ├── feedback.py         # Feedback collection
    │   ├── trace.py            # Trace analysis
    │   └── metrics.py          # Aggregate metrics
    └── environment/            # Domain scaffolding (user interaction, game logic)
        └── cli/
            └── __main__.py     # Typer CLI (run + loop with auto-commit)
```

### Design Patterns

#### Persistent Agent Pattern

For agents that exist over time — maintaining conversations, monitoring systems, playing games — the architecture inverts: the agent is a **persistent presence** that controls its own attention, not a processor steered by an event queue.

| Do This                                                     | Not This                                    |
| ----------------------------------------------------------- | ------------------------------------------- |
| Agent sleeps when it chooses, wakes on events               | Event queue drives agent responses          |
| All timing is tools (sleep, debounce, remind, schedule)     | Hardcode delays or polling in orchestration |
| Stop hook prevents turn from ending — only sleep yields     | Request-response per event                  |
| Pull-based state reading (agent calls `context` when ready) | Push state changes as SDK user turns        |
| Agent parks thoughts (ideas, reminders) for later           | Drop context between interactions           |
| Expose environment state as tool-readable data              | Hide activity from the agent                |

**The core loop:** The agent never ends its turn. A Stop hook blocks it. Instead it cycles: wake → read context → think → act → meta-assess → sleep. The only way to yield control is `sleep()`, which blocks on an asyncio Event until something wakes it.

**Why not an event queue?** The sleep/wake pattern lets the agent stay centered — it can debounce event bursts, schedule actions, set reminders, and park thoughts for later, all on its own terms.

**Library support:** `src/lup/lib/realtime.py` provides the `Scheduler` class and hook factories (`create_stop_guard`, `create_pending_event_guard`). See example tools in `src/lup/agent/tools/realtime.py`.

#### Reflection Pattern

Agents produce better output when forced to self-assess before committing. Three components:

1. **Reflection tool** (`agent/tools/reflect.py`): Domain-customizable self-assessment — confidence, uncertainties, tool audit, process reflection. Optionally runs a reviewer sub-agent.
2. **Reflection gate** (`lib/reflect.py`): `ReflectionGate` flag tracker + `create_reflection_gate()` hook factory. Denies a target tool until reflection occurs.
3. **Wiring**: The gate blocks `StructuredOutput` (one-shot agents) or `sleep` (persistent agents) until reflection occurs.

**Customizing:** The gate in `lib/reflect.py` is domain-neutral and parametric. The reflection tool and `ReflectInput` in `agent/tools/reflect.py` are domain-specific — add fields for your domain. The reviewer prompt should target your domain's common failure modes.

**Skip reviewer:** Set `skip_reviewer=True` for speed-sensitive or trivial tasks. The reviewer adds latency but catches calibration errors and reasoning gaps.

#### Parametric Library Design

Files in `src/lup/lib/` must be **complete-as-is and configurable through function arguments** — never by modifying the source. Domain-specific code belongs in `agent/`.

- **Use function parameters** for customization (callbacks, config objects, path overrides)
- **Use `configure()`-style functions** for module-level state that needs overriding
- **No imports from `agent/`** in lib code — the dependency arrow points one way

---

## Getting Started

### Commands

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
uv run python -m lup.environment.cli run "your task here"
uv run python -m lup.environment.cli run --session-id my-session "task"

# Run multiple sessions with auto-commit
uv run python -m lup.environment.cli loop "task1" "task2" "task3"
uv run python -m lup.environment.cli loop --no-commit "task1" "task2"

# Commit uncommitted session results
uv run lup-devtools git commit-results
uv run lup-devtools git commit-results --dry-run

uv run python -m lup.environment.cli --help
```

### Testing

```bash
uv run pytest                      # All tests
uv run pytest -v                   # Verbose
uv run pytest tests/test_file.py   # Specific file
uv run pytest -k "test_name"       # Pattern match
```

**Organization:** `tests/unit/` (mock external APIs), `tests/integration/` (require API keys, `@pytest.mark.integration`).

### Test Principles

**Test behavior, not construction.** Never test that a constructor sets attributes — that's testing the framework (Pydantic, dataclasses), not your code. If a class is a pure data container with no methods, computed properties, or custom validation, it doesn't need tests.

**Every test should answer: "what could go wrong?"** If nothing can go wrong (e.g., `assert artifact.name == "solution.py"` after setting `name="solution.py"`), the test is worthless. Good tests exercise:

- **State transitions** — does adding then removing leave the system clean?
- **Edge cases** — empty inputs, missing files, duplicate names, boundary values
- **Invariants** — properties that must hold across operations (e.g., cleanup stops all sandboxes)
- **Integration points** — does the code read from disk correctly? Does it compose with its dependencies?

**The test for a test:** Remove it. Does the remaining suite still catch real bugs? If yes, the test was dead weight.

| Write Tests For | Don't Write Tests For |
|---|---|
| Computed properties that read from disk | Pydantic model construction |
| Registry CRUD with state verification | Attribute access after `__init__` |
| Error paths and graceful degradation | Default field values |
| Multi-step workflows (add → use → remove) | Constants (`assert "Bash" in BUILTIN_TOOLS`) |
| Concurrency and timing behavior | Sorted output of deterministic functions |

### Debugging

**Do not hypothesize — trace.** Find actual logs, read the exact exception. Do not list "likely causes" or suggest the user check things. Open log files, grep for the error, read the traceback, report what actually happened. If logs lack info, say exactly what logging to add and where.

Use `/lup:debug <error message>` to trace an error through logs automatically.

### Feedback Loop Scripts

```bash
uv run lup-devtools feedback collect --all-time
uv run lup-devtools trace list
uv run lup-devtools trace show <session_id>
uv run lup-devtools metrics summary
```

### Customizing for Your Domain

1. **Run `/lup:brainstorm`** (optional) — Explore architecture, MCP tools, and agent design before committing to scaffolding. Produces a `DESIGN.md` that init reads as context.
2. **Run `/lup:init`** — Walks through domain customization (what the agent does, how outcomes are measured, what metrics matter)
3. **Models** (`agent/models.py`) — `AgentOutput`, `Factor`, `SessionResult`
4. **Subagents** (`agent/subagents.py`) — Specialized subagents, tool sets, model choices
5. **Tools** (`agent/tool_policy.py`) — API key requirements, conditional availability, MCP configs
6. **Reflection** (`agent/tools/reflect.py`) — Domain-specific `ReflectInput` fields, reviewer prompt
7. **Version** (`version.py`) — Set initial `AGENT_VERSION`, bump on behavior changes
8. **Persistent mode** (optional) — Wire `Scheduler` from `lib/realtime.py`, add Stop hook, implement sleep/context/reply tools, replace request-response with sleep/wake loop
9. **Feedback** (`devtools/feedback.py`) — Implement `load_outcomes()`, customize `compute_metrics()`

---

## Development Workflow

### Git Workflow

This project uses **git worktrees** (not regular branches) to develop multiple features in parallel.

**IMPORTANT:** Never commit _code_ directly to `dev`. Always work in a worktree for code changes.

**Exception:** Data commits (`data(outputs):`) can go directly to `dev` — generated outputs don't need review.

### Two-Tier Branch Model

- **`dev`** = integration branch. Feature PRs merge here. Day-to-day development target.
- **`main`** = stable branch. Only receives PRs from `dev`. Branch-protected on GitHub.

Worktrees typically branch from `dev`, but can also branch from other feature branches. Feature PRs target `dev` (or the branch they diverged from). Periodically, `dev` is merged into `main` via a reviewed PR.

**Worktrees vs branches:**

- `git checkout -b` — Creates a branch, stays in same directory. Switching changes all files in place.
- `git worktree add` — Creates a new directory with its own working copy. Multiple branches simultaneously.

**If already in a worktree:** Check with `git worktree list`. If you're in a feature worktree, just work directly — no need to create another.

**Feature workflow:**

1. `git worktree add ./worktrees/feat-name -b feat/feature-name && cd ./worktrees/feat-name`
2. Commit regularly and atomically
3. Push when complete (or periodically for backup)
4. `/lup:rebase` — Push, open PR, clean up history with `git reset --soft main` and force-push
5. Review — Fix issues, re-run `/lup:rebase` to rebuild history
6. `/lup:close` — Merge approved PR and clean up

**Note:** The `worktrees/` and `refs/` directories are gitignored. `refs/` contains symlinks to downstream projects.

### Merge Conflict Resolution

**Never silently drop code during conflict resolution.** The bias is toward inclusion -- keeping both sides is always safer than losing features. A rename on one side must not swallow an addition on the other.

Before completing any merge, **audit for deletions**: compare the result against both parents and verify that every removed function, parameter, or command was intentionally removed, not lost as a side effect of choosing one conflict side.

Use `/lup:merge-conflict` for guided resolution. See the command for the full decision tree.

### Commit Guidelines

- **Commit before responding** — Don't accumulate changes across responses
- **Commit early, commit often** — Frequent commits provide checkpoints
- **Keep commits atomic** — If you need "and" in your message, it should be two commits
- **History will be rebased** — Don't worry about perfect messages during development

**Format:** `type(scope): description`

| Type       | Use                                                                  |
| ---------- | -------------------------------------------------------------------- |
| `feat`     | New feature or capability                                            |
| `fix`      | Bug fix                                                              |
| `refactor` | Code change that neither fixes a bug nor adds a feature              |
| `docs`     | Documentation only (README, standalone docs)                         |
| `test`     | Adding or updating tests                                             |
| `chore`    | Maintenance (dependencies, build config)                             |
| `meta`     | Changes to `.claude/` files (CLAUDE.md, settings, scripts, commands) |
| `data`     | Generated data and outputs                                           |

### Editing Style

**Prefer small, atomic edits.** A PreToolUse hook counts "real" changed lines (ignoring imports, comments, whitespace, blank lines, docstrings) and auto-allows edits with <=3 real changes. Pure deletions, TypedDict/BaseModel definitions, and single-line `replace_all` renames are always auto-allowed.

- Split large changes into multiple small edits (<=3 real lines per Edit call)
- Separate concerns — imports in one edit, logic in another
- Use `rename-symbol` for identifier renames instead of `Edit` with `replace_all`

---

## Code Conventions

### Primary Libraries

- **claude-agent-sdk**: Primary framework for building agents (use `query()` for one-shot LLM calls with structured output)
- **pydantic**: For data validation and settings
- **pydantic-settings**: For configuration (not dotenv)

### Type Safety

- **No bare `except Exception`** — always catch specific exceptions
- **Every function must specify input and output types**
- **Never use `Any`, `dict[str, Any]`, or `dict[str, object]`** — Use `TypedDict` for dict-like data, `BaseModel` for validated models, or specific types
  - **MCP tool inputs**: `BaseModel.model_validate(args)` immediately — don't pass around raw dicts
  - **MCP tool outputs**: Define a `TypedDict` for the return dict
  - **SDK hooks**: Return `SyncHookJSONOutput` from `claude_agent_sdk.types`. Use typed hook inputs (`PreToolUseHookInput`, etc.) and specific output types (`PreToolUseHookSpecificOutput`, etc.)
  - **SDK types to prefer**: `HookMatcher`, `AgentDefinition`, `ClaudeAgentOptions`, `McpServerConfig`, `PermissionResultAllow`/`Deny`, `ContentBlock`, `Message`, `TextBlock`, `ToolUseBlock`, `ToolResultBlock`. Import from top-level `claude_agent_sdk` when available; `SyncHookJSONOutput`, `HookEvent`, and hook-specific types require `claude_agent_sdk.types`.
- **Python 3.12+ generics**: `class A[T]`, not `Generic[T]`
- Use `TypedDict` and Pydantic models for structured data
- Never manually parse agent output — use structured outputs via Pydantic
- **Never use `# type: ignore`** — Ask the user how to properly fix type errors
- **Use Pydantic BaseModel instead of dataclasses**
- **Use `match`/`case` instead of `if`/`elif` chains** for dispatching on values or ranges

### Tool Input Schemas

Define tool inputs as BaseModel classes with `Field(description=...)`:

| Do This                                                               | Not This                       |
| --------------------------------------------------------------------- | ------------------------------ |
| `class SearchInput(BaseModel): query: str = Field(description="...")` | `{"query": str, "limit": int}` |
| `SearchInput.model_json_schema()` for `@tool` schema                  | Hand-written dict schemas      |
| `SearchInput.model_validate(args)` then `params.query`                | `args.get("query", "")`        |

### Error Handling

**MCP tools:** Return `{"content": [...], "is_error": True}` for recoverable errors. Log with `logger.exception()`. Include actionable messages.

**Agent code:** Raise exceptions for unrecoverable errors. Use `with_retry` for transient failures. Validate inputs early with Pydantic.

**Never silently swallow errors** — handle them meaningfully or let them propagate.

### Structured Data, Not Strings

If you're reaching for `re`, `.replace()`, `.split()`, or string slicing to process structured data, something is wrong:

- **Web pages**: `trafilatura` for text extraction, `beautifulsoup4` for DOM
- **XML**: `xml.etree.ElementTree` or `lxml`
- **JSON**: `json.loads()`, not regex
- **SDK objects**: Filter `ContentBlock` lists by type and attribute
- **Dates**: Parse to `datetime`, don't compare strings
- **URLs**: `urllib.parse`, not splitting
- **Paths**: `pathlib.Path`, not concatenation

`import re` is a code smell — look for the structured API first.

### Standard Libraries

Use existing Python libraries from PyPI before writing raw HTTP requests. Don't rebuild the wheel.

### Code as Documentation

The codebase should read as a **monolithic source of truth** — understandable without knowledge of its history.

**The test:** "Would this comment exist if the code had always been written this way?" If no — don't add it.

- Never reference what code used to do or explain modifications you made
- Never use "now", "new", "updated", "fixed", or "changed" in comments
- Use commit messages for change history, not code comments

### DRY: Don't Repeat Yourself

- If logic exists in `lib/`, import it. Don't copy-paste.
- Utilities belong in `lib/`, not `agent/`. `agent/` imports from `lib/`.
- **Placement test:** Can this module be used as-is without templating or source modification? If yes → `lib/`. Quick proxy: does it import from `agent/`?

### Naming: No Private Prefixes

**Never use `_` prefixes** on functions, methods, classes, or constants. Nothing is private.

- Module-level functions: just name them `build_options`, not `_build_options`
- Class methods: `remove_stale_container`, not `_remove_stale_container`
- Constants: `PACE_THRESHOLDS`, not `_PACE_THRESHOLDS`
- Classes: `PendingReminder`, not `_PendingReminder`

**If a helper truly shouldn't pollute the module namespace**, nest it inside its only caller:

```python
def build_display(usage, stats):
    def place_label(text, position, width):
        ...
    # use place_label here
```

**Avoid useless mini-wrappers.** If a function's only purpose is to call another function with no additional logic, inline it.

**Exceptions:** `_` prefix is fine for unused parameters (`_context`, `_exc_type`) — that's a linting convention, not a privacy convention.

---

## Tooling

### Package Tools

- **uv**: Package manager. Use `uv add <package>` (never edit pyproject.toml directly)
- **ruff**: Formatting and linting
- **pyright**: Type checking

### lup-devtools

All development tooling lives in `src/lup/devtools/` and is exposed as the `lup-devtools` CLI entry point. **Always use `lup-devtools` instead of ad-hoc commands.** Never use `uv run python -c "..."` or bare `python`/`python3` — these are denied by the Bash permission hook.

If you find yourself running the same command repeatedly, **add a command** to `src/lup/devtools/`. Use `tmp/*.py` for one-off scripts.

**Write scripts in Python using [typer](https://typer.tiangolo.com/)** for CLIs. Use **[sh](https://sh.readthedocs.io/)** for shell commands instead of `subprocess`.

```
lup-devtools
├── agent                   # Agent introspection and debugging
│   ├── inspect             # Show tools, schemas, prompt, subagents
│   ├── serve-tools         # Start SDK tools as MCP stdio server
│   └── chat                # Launch interactive claude with agent config
├── api                     # API inspection and module info
│   ├── inspect <path>      # Explore Python module/class/method APIs
│   ├── module-path <mod>   # Show file path for a module
│   ├── module-source <mod> # Show source code for a module
│   ├── module-tree <mod>   # Show file tree for a package
│   └── module-info <mod>   # Show detailed info about a module
├── dev                     # Development tools
│   └── worktree <name>     # Create git worktree with plugin refresh
├── git                     # Git operations for sessions
│   └── commit-results      # Commit uncommitted session results
├── sync                    # Upstream sync tracking (/lup:update)
│   ├── list                # Show tracked projects and sync status
│   ├── log <project>       # Show commits since last sync
│   ├── diff <project> <sha># Show full diff for a commit
│   ├── mark-synced <proj>  # Mark project as synced at HEAD
│   └── setup <name> <path> # Set local path for a project
├── usage                   # Claude Code live usage display
├── feedback                # Feedback collection
│   ├── collect             # Collect feedback metrics from sessions
│   └── check               # Check available feedback data
├── trace                   # Trace analysis
│   ├── list                # List available traces
│   ├── show <id>           # Show trace for a session
│   ├── search <pattern>    # Search traces for a regex pattern
│   ├── errors              # Show sessions with errors
│   └── capabilities        # Extract capability requests
└── metrics                 # Aggregate metrics
    ├── summary             # Show aggregate summary
    ├── tools               # Show tool usage aggregates
    ├── errors              # Show sessions with high error rates
    ├── trends              # Show metric trends over time
    └── history             # Show previous feedback collection runs
```

### Permission Hooks

Permissions are managed by **PreToolUse hook scripts** in `.claude/plugins/lup/hooks/scripts/`:

| Hook                  | Tool            | Config                                                             |
| --------------------- | --------------- | ------------------------------------------------------------------ |
| `auto_allow_fetch.py` | WebFetch        | `ALLOW_PATTERNS` (regex), `DENY_PATTERNS` (regex + reason)        |
| `auto_allow_bash.py`  | Bash            | `RULES` list of `Allow`/`Deny` (last-match-wins, like .gitignore) |
| `auto_allow_edits.py` | Edit            | Trivial-line counting, protected file list                         |
| `pre_push_check.py`   | Bash (git push) | Runs pyright, ruff, pytest before push                             |
| `check_plan_md.py`    | Bash (git push) | Warns if PLAN.md missing on feature branches                       |
| `protect_tests.py`    | Edit\|Write     | TDD mode test protection                                          |

To add a new allowed URL or command, edit the pattern list in the corresponding hook. Non-matching inputs fall through to user prompt.

`settings.json` only contains rules that don't need regex: `WebSearch` (allow), `Read(.local)` (deny), `Edit(pyproject.toml)` (ask).

### Pyright LSP

The `pyright-lsp` plugin provides code intelligence. **Use these actively** — faster and more accurate than grep for code understanding.

**Navigation:**

- **go-to-definition** — Jump to where a symbol is defined (instead of grepping for `def foo`)
- **find-references** — Find all usages (instead of grepping for a symbol name)
- **hover-documentation** — Type info and docs at a position
- **list-symbols** — All symbols in a file (instead of grepping for `def ` or `class `)
- **find-implementations** — Implementations of an interface/abstract method
- **trace-call-hierarchy** — Understand call chains

**Refactoring:**

- **rename-symbol** — Rename across workspace. **Always prefer over `Edit` with `replace_all`** — understands scope.

| Task                             | LSP                | grep/Edit        |
| -------------------------------- | ------------------ | ---------------- |
| Find where a function is defined | `go-to-definition` |                  |
| Find all callers of a function   | `find-references`  |                  |
| Rename a variable/function/class | `rename-symbol`    |                  |
| Search for a string literal      |                    | `Grep`           |
| Search across non-Python files   |                    | `Grep`           |
| Change logic within a function   |                    | `Edit`           |
| Add new code                     |                    | `Edit` / `Write` |

---

## Configuration

### Environment Variables

The `.env` file contains template configuration. Create `.env.local` for secrets (gitignored):

```bash
# .env.local - your secrets (ANTHROPIC_API_KEY is read directly by the SDK from env)

# Optional overrides
# AGENT_MODEL=claude-sonnet-4-20250514
# AGENT_MAX_BUDGET_USD=5.00
```

Settings in `.env.local` override `.env`. Configuration is loaded via pydantic-settings — see `src/lup/agent/config.py`.

All Claude Code settings modifications should be **project-level** (in `.claude/settings.json`), not user-level.

---

## Process & Communication

### Asking Questions

**Always use the `AskUserQuestion` tool** instead of asking questions in plain text. This applies to clarifying requirements, offering choices, confirming destructive actions, proposing changes, and any situation needing user input.

Even for open-ended questions, use `AskUserQuestion` with options that include a custom input option. This allows structured notification parsing.

**When proposing changes:** Propose (don't assume), show relevant current state, explain rationale, offer alternatives.

**When in doubt, ask.**

### Planning & Documentation

**PLAN.md** is the source of truth for what has been built and what remains:

- Reflect actual state, not aspirational designs
- Mark completed items (`[x]`), keep status indicators current (`[ ]` pending, `[~]` in progress)
- Update architecture decisions as they evolve
- Add new tasks discovered during implementation
- No speculative code — describe what to build, not how

### Slash Commands & Skills

**After every command invocation**, reflect on how it was actually used vs. documented:

1. Compare intent vs usage
2. Notice patterns — user corrections signal the command should evolve
3. Proactively propose updates via AskUserQuestion

**Evolution signals:** User provides external docs, corrects your approach, asks for something the command should cover, or ignores sections.

### External Resources

When questions involve Claude Code, Agent SDK, or Claude API:

1. Use the `claude-code-guide` subagent: `Task(subagent_type="claude-code-guide", prompt="...")`
2. Fetch docs directly: `WebFetch(url="https://docs.claude.com/en/agent-sdk/<topic>")`

When the user provides documentation links, incorporate that knowledge into CLAUDE.md or relevant commands.

---

## Self-Improvement Loop

See [The Bitter Lesson](#the-bitter-lesson) and [Tool Design Philosophy](#tool-design-philosophy) — these govern all agent improvements.

**When analyzing failures:** Ask "what general principle would have prevented this?" not "what specific rule would catch this case?" The fix is almost never a prompt line about a specific decision. Instead: does the agent have enough context? The right tools? A strong enough model?

### Three Levels of Analysis

1. **Object Level** — The agent itself: tools, capabilities, behavior
2. **Meta Level** — The agent's self-tracking: what it monitors about itself
3. **Meta-Meta Level** — The feedback loop process: scripts, analysis methods

### Running the Feedback Loop

1. **Collect feedback**: `uv run lup-devtools feedback collect`
2. **Read traces deeply**: Read 5-10 sessions in detail — don't skip to aggregates
3. **Extract patterns**: Tool failures, capability requests, reasoning quality
4. **Implement changes**: Fix tools → Build requested capabilities → Simplify prompts
5. **Update documentation**: This file should evolve with the agent

### What to Track Per Session

- **Sessions**: `notes/traces/<version>/sessions/<session_id>/`
- **Outputs**: `notes/traces/<version>/outputs/<task_id>/`
- **Traces**: `notes/traces/<version>/logs/<session_id>/`
- **Metrics**: Tool calls, timing, errors via metrics tracking

---

## Anti-Patterns

- Adding numeric patches ("subtract 10% from estimates")
- Prompting Lup with rigid mechanical procedures instead of guidelines and rationale
- Adding absolute thresholds ("if X happens N times, do Y")
- Adding rules the agent can't act on (no access to required data)
- Making small edits to patch one mistake instead of finding the general cause
- Listing tools by name in the system prompt (two sources of truth that drift apart)
- Writing terse tool descriptions
- Skipping trace analysis to jump to aggregate statistics
- Over-engineering initial implementations
- Making changes in `lup.environment` when `lup.agent` is the right place

**Questions to ask when proposing changes:**

1. Does this add a capability or just a rule?
2. Would this help if the domain changed completely?
3. Are we changing the right level (object/meta/meta-meta)?
4. What general principle would have prevented this failure?
5. What data would we need to validate this change worked?
