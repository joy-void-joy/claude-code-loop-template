---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, AskUserQuestion
description: Initialize the self-improvement loop for a specific domain
---

# Initialize Self-Improvement Loop

This command sets up the project identity, renames the source package, and customizes the feedback collection, metrics, and trace analysis for your specific agent domain.

**This project uses the Claude Agent SDK.** The Agent SDK is the default and expected framework. If the user wants to use the bare Anthropic API instead, ask them to explain why — the Agent SDK provides structured outputs, tool use, subagents, and hooks out of the box.

## Your Task

Interview the user about their domain, rename the source package, and generate the appropriate scaffolding.

## Phase 1: Project Identity

Use AskUserQuestion to determine the project name:

### 1. Project Name
- What should the project be called? This becomes the Python package name.
- Must be a valid Python identifier (lowercase, underscores, no hyphens or spaces).
- Examples: `aib`, `forecast_bot`, `coach`, `game_agent`

### 2. Agent Purpose
- What does the agent do? (forecasting, coaching, game playing, task completion, etc.)
- What is a "session" or "run"? (one forecast, one conversation, one game, one task)

### 3. Ground Truth & Success Metrics
- How do you know if the agent did well?
  - **External ground truth**: Outcomes that resolve later (predictions, game wins, task success)
  - **Human feedback**: Ratings, corrections, preferences
  - **Proxy metrics**: Engagement time, task completion, coherence scores
  - **Self-assessment**: Agent's own meta-reflection quality
  - **No clear ground truth**: Focus on process quality and trace analysis

### 4. What to Track
- What outputs should be saved per session?
- What metrics matter? (accuracy, cost, time, tool usage, user satisfaction)
- What trace data is valuable? (reasoning, tool calls, intermediate states)

### 5. Feedback Sources
- Where does feedback come from?
  - Resolution/outcome data
  - User ratings or corrections
  - Comparison against baselines
  - Expert review
  - Automated quality checks

### 6. Task Format
- How are tasks provided to the agent? (free text, IDs, files, API calls)
- Should the `loop` CLI command batch-process them?
- What does auto-commit look like for this domain?

## Interviewing Style

Use AskUserQuestion extensively — don't make assumptions about the domain. Ask open-ended questions first, then drill into specifics. Example questions (adapt based on context):

- "What should this project be called? (valid Python package name, e.g., 'aib', 'forecast_bot')"
- "What does your agent do and what does a single session look like?"
- "How do you know if the agent did well? Is there ground truth that resolves later?"
- "What metrics matter most to you?"
- "How are tasks provided — free text, IDs, files, API calls?"
- "Should results auto-commit after each session?"
- "What tools or APIs will the agent need?"

Let the conversation flow naturally. The goal is to understand the domain well enough to customize the template files below.

## Phase 2: Rename Package

Rename `src/lup/` to `src/<project>/` where `<project>` is the name from Phase 1.

### Steps:

1. **Rename the directory**:
   ```bash
   git mv src/lup src/<project>
   ```

2. **Update all Python imports** — find and replace across all files:
   - `from lup.` → `from <project>.`
   - `import lup` → `import <project>`
   - In source files under `src/<project>/`
   - In test files under `tests/`

3. **Update `pyproject.toml`**:
   - `name = "lup-template"` → `name = "<project>"`
   - `[project.scripts]`: `lup = "lup.environment.cli.__main__:app"` → `<project> = "<project>.environment.cli.__main__:app"`

4. **Update CLI** (`src/<project>/environment/cli/__main__.py`):
   - `app = typer.Typer(name="lup", ...)` → `name="<project>"`

5. **Update CLAUDE.md** — replace all `src/lup/` with `src/<project>/`, `lup.agent` with `<project>.agent`, etc. Use a script in `./tmp/` for bulk replacements.

6. **Update logger names** in `src/<project>/lib/trace.py`:
   - `"lup.agent.stream"` → `"<project>.agent.stream"`

7. **Verify**:
   ```bash
   uv sync
   uv run pyright
   uv run ruff check .
   uv run pytest
   <project> --help
   ```

**Important:** The plugin stays as `.claude/plugins/lup/` — that's the framework identity, not the project identity. Only the source package and pyproject.toml change.

## Phase 3: Generate Scaffolding

Based on the answers from Phase 1, generate or modify:

### 1. `src/<project>/agent/models.py`
Customize AgentOutput for the domain:
- Add domain-specific fields (probability, move, response, etc.)
- Add domain-specific columns to `src/<project>/lib/scoring.py` CSV_COLUMNS

### 2. `src/<project>/agent/prompts.py`
Update the system prompt template for the domain.

### 3. `src/<project>/agent/subagents.py`
Create domain-appropriate subagents (researcher, analyzer, etc.)

### 4. `src/<project>/environment/cli/__main__.py`
Customize the CLI for the domain's task format:
- Update the `loop` command to accept domain-specific task inputs
- Customize `_commit_results()` message format (e.g., `data(forecasts):` instead of `data(sessions):`)
- Configure auto-commit behavior: enable/disable by default, target branch (main for data-only commits, or a dedicated branch)
- Add domain-specific CLI commands if needed

### 5. `src/<project>/version.py`
Set initial AGENT_VERSION and explain bump rules for this domain.

### 6. `feedback_collect.py`
The main feedback collection script. Customize for the domain's ground truth type.

### 7. Update `CLAUDE.md`
Add domain-specific sections:
- Project overview with domain description
- Commands specific to the domain
- Metrics and feedback collection instructions

### 8. Update `feedback-loop.md`
Customize the feedback loop command for the domain's specific:
- Ground truth type
- Metrics to analyze
- Trace inspection approach

## Phase 4: Verify Setup

After generating files:

1. Run `uv run pyright` to check types
2. Run `uv run ruff check .` to check lint
3. Run `uv run python -m <project>.environment.cli --help` to verify CLI
4. Verify the feedback loop command references the right scripts
5. Check that CLAUDE.md accurately describes the domain

## After Initialization

Once the scaffolding is generated, guide the user to:

1. Run a few sessions: `uv run python -m <project>.environment.cli loop "task1" "task2"`
2. Review traces in `notes/traces/`
3. Check scores in `notes/scores.csv`
4. Use `/lup:feedback-loop` to analyze and improve
5. Iterate on the feedback collection as patterns emerge

## Key Files to Customize

- `src/<project>/agent/models.py` — Output schemas (AgentOutput, SessionResult)
- `src/<project>/agent/subagents.py` — Specialized subagents
- `src/<project>/agent/tool_policy.py` — Tool availability and MCP servers
- `src/<project>/agent/core.py` — Options building and orchestration
- `src/<project>/agent/prompts.py` — System prompt templates
- `src/<project>/environment/cli/__main__.py` — CLI with loop + auto-commit
- `src/<project>/lib/scoring.py` — CSV columns and score row building
- `src/<project>/version.py` — Agent version tracking
- `.claude/plugins/lup/scripts/loop/feedback_collect.py` — Feedback collection
