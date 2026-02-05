# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

This is a **self-improving agent template** built with the Claude Agent SDK. The template provides scaffolding for building agents that can review their own traces and improve over time through a structured feedback loop.

Built with Python 3.13+ and the Claude Agent SDK. Uses `uv` as the package manager.

### Key Concepts

- **Loop Package** (`src/loop/`): The package containing all code for the self-improving agent.
  - **Agent Subpackage** (`src/loop/agent/`): The agent code that the feedback loop improves. Contains core orchestration, tools, subagents, and configuration.
  - **Environment Subpackage** (`src/loop/environment/`): Domain-specific scaffolding (user interaction, game logic, etc.). Evolves with application requirements, but not via the feedback loop.
- **Three-Level Meta Analysis**: Object (agent behavior), Meta (agent self-tracking), Meta-Meta (feedback loop process).

---

## Getting Started

### Reference Files

**Agent (customize for your domain):**
- **src/loop/agent/core.py**: Main agent orchestration
- **src/loop/agent/config.py**: Configuration via pydantic-settings
- **src/loop/agent/models.py**: Output models
- **src/loop/agent/subagents.py**: Subagent definitions
- **src/loop/agent/tool_policy.py**: Conditional tool availability
- **src/loop/agent/tools/example.py**: Example MCP tools

**Library (reusable abstractions):**
- **src/loop/lib/hooks.py**: Hook utilities and composition
- **src/loop/lib/trace.py**: Trace logging and output formatting
- **src/loop/lib/metrics.py**: Tool call tracking

**Environment:**
- **src/loop/environment/cli/__main__.py**: Typer CLI that runs the agent

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

# Run the agent CLI
uv run python -m loop.environment.cli run "your task here"
uv run python -m loop.environment.cli run --session-id my-session "task"
uv run python -m loop.environment.cli --help
```

### Feedback Loop Scripts

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

## Customization Guide

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

### Step 5: Update Feedback Collection

Edit `.claude/plugins/loop/scripts/feedback_collect.py`:
- Implement `load_outcomes()` for your domain
- Customize `compute_metrics()` for your metrics
- Add domain-specific summary output

---

## Development Workflow

### Directory Structure

```
src/
└── loop/
    ├── lib/                    # Reusable abstractions (rarely modified)
    │   ├── cache.py            # TTL caching for API responses
    │   ├── history.py          # Session storage/retrieval
    │   ├── hooks.py            # Claude Agent SDK hook utilities
    │   ├── metrics.py          # Tool call tracking (@tracked decorator)
    │   ├── mcp.py              # MCP server creation utilities
    │   ├── notes.py            # RO/RW directory structure
    │   ├── responses.py        # MCP response formatting
    │   ├── retry.py            # Retry decorator with backoff
    │   └── trace.py            # Trace logging and output formatting
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
            └── __main__.py     # Typer CLI application
```

### Code Style

- **No bare `except Exception`** — always catch specific exceptions
- **Every function must specify input and output types**
- Use `TypedDict` and Pydantic models for structured data
- Never manually parse agent output — use structured outputs via Pydantic
- **Use Pydantic BaseModel instead of dataclasses**

### DRY: Don't Repeat Yourself

- **Never duplicate code** — If logic exists in `lib/`, import it. Don't copy-paste.
- **Utilities belong in `lib/`** — Functions like `print_block`, `TraceLogger`, formatters go in lib, not agent.
- **`agent/` imports from `lib/`** — The agent layer uses lib abstractions, never redefines them.
- **Check before writing** — Before creating a utility, search lib/ for existing implementations.

### Commit Guidelines

Use conventional commit syntax: `type(scope): description`

**Types:**
- `feat` — New feature or capability
- `fix` — Bug fix
- `refactor` — Code change that neither fixes a bug nor adds a feature
- `meta` — Changes to `.claude/` files
- `data` — Generated data and outputs

---

## Self-Improvement Loop

### The Bitter Lesson

When improving the agent, prefer:

| Do This | Not This |
|---------|----------|
| Add tools that provide data | Add prompt rules that constrain behavior |
| Apply general principles | Apply specific pattern patches |
| Provide state/context via tools | Use f-string prompt engineering |
| Create subagents for specialized work | Build complex pipelines in main agent |

### Three Levels of Analysis

1. **Object Level** — The agent itself: tools, capabilities, behavior
2. **Meta Level** — The agent's self-tracking: what it monitors about itself
3. **Meta-Meta Level** — The feedback loop process: scripts, analysis methods

### Running the Feedback Loop

1. **Collect feedback**: `uv run python .claude/plugins/loop/scripts/feedback_collect.py`
2. **Read traces deeply**: Don't skip to aggregates. Read 5-10 sessions in detail.
3. **Extract patterns**: Tool failures, capability requests, reasoning quality
4. **Implement changes**: Fix tools → Build requested capabilities → Simplify prompts
5. **Update documentation**: This file should evolve with the agent

### What to Track Per Session

- **Outputs**: Final results saved to `notes/sessions/<session_id>/`
- **Traces**: Reasoning logs saved to `notes/traces/<session_id>/`
- **Metrics**: Tool calls, timing, errors via metrics tracking

---

## Configuration

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

## Anti-Patterns to Avoid

- ❌ Adding numeric patches ("subtract 10% from estimates")
- ❌ Adding rules the agent can't act on (no access to required data)
- ❌ Skipping trace analysis to jump to aggregate statistics
- ❌ Over-engineering initial implementations
- ❌ Making changes in `loop.environment` when `loop.agent` is the right place

### Questions to Ask

When proposing changes:
1. Does this add a capability or just a rule?
2. Would this help if the domain changed completely?
3. Are we changing the right level (object/meta/meta-meta)?
4. What data would we need to validate this change worked?
