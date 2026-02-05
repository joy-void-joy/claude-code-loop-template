# CLAUDE.md Template

Use this as a starting point for your project's CLAUDE.md. Customize each section for your domain.

---

# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**[Describe your agent and what it does]**

Built with Python 3.13+ and the Claude Agent SDK. Uses `uv` as the package manager.

### Important Context

**[Add domain-specific context here. Examples:]**
- What outcomes matter and how they're measured
- What data sources are available
- What constraints or limitations exist

---

## Getting Started

### Reference Files

- **src/loop/agent/core.py**: Main agent orchestration
- **src/loop/agent/subagents.py**: Subagent definitions
- **src/loop/agent/tools/**: Tool implementations
- **src/loop/environment/client.py**: Domain scaffolding (user interaction, game logic)
- **.claude/plugins/loop/scripts/**: Feedback loop scripts

### Commands

```bash
# Install dependencies
uv sync

# Run the agent
uv run agent <arguments>

# Add a new dependency
uv add <package-name>

# Format and lint
uv run ruff format .
uv run ruff check .
uv run pyright
```

### Feedback Loop

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

## Development Workflow

### Git Workflow

**[Add your git workflow here. Consider using worktrees for parallel feature development.]**

### Commit Guidelines

Use conventional commit syntax: `type(scope): description`

**Types:**
- `feat` — New feature or capability
- `fix` — Bug fix
- `refactor` — Code change that neither fixes a bug nor adds a feature
- `meta` — Changes to `.claude/` files
- `data` — Generated data and outputs

---

## Code Style & Patterns

### Type Safety

- **No bare `except Exception`** — always catch specific exceptions
- **Every function must specify input and output types**
- Use `TypedDict` and Pydantic models for structured data
- Never manually parse agent output — use structured outputs via Pydantic

### Error Handling

**MCP tools should:**
- Return `{"content": [...], "is_error": True}` for recoverable errors
- Log exceptions with `logger.exception()` for debugging
- Include actionable error messages

**Agent code should:**
- Raise exceptions for unrecoverable errors
- Use retry decorators for transient failures
- Validate inputs early with Pydantic models

### The Bitter Lesson

When improving the agent, prefer:

| Do This | Not This |
|---------|----------|
| Add tools that provide data | Add prompt rules that constrain behavior |
| Apply general principles | Apply specific pattern patches |
| Provide state/context via tools | Use f-string prompt engineering |
| Create subagents for specialized work | Build complex pipelines in main agent |

---

## Self-Improvement Loop

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

## First Principles

### Design Philosophy

1. **Capabilities over constraints**: Give the agent more tools, not more rules
2. **General over specific**: Changes should help even if the domain shifts
3. **Process over patches**: Improve the feedback loop, not just individual behaviors

### Anti-Patterns to Avoid

- ❌ Adding numeric patches ("subtract 10% from estimates")
- ❌ Adding rules the agent can't act on (no access to required data)
- ❌ Skipping trace analysis to jump to aggregate statistics
- ❌ Over-engineering initial implementations

### Questions to Ask

When proposing changes:
1. Does this add a capability or just a rule?
2. Would this help if the domain changed completely?
3. Are we changing the right level (object/meta/meta-meta)?
4. What data would we need to validate this change worked?
