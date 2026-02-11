---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, AskUserQuestion
description: Initialize the self-improvement loop for a specific domain
---

# Initialize Self-Improvement Loop

This command sets up the feedback collection, metrics, and trace analysis for your specific agent domain.

## Your Task

Interview the user about their domain and generate the appropriate scaffolding.

## Phase 1: Understand the Domain

Use AskUserQuestion to gather information about:

### 1. Agent Purpose
- What does the agent do? (forecasting, coaching, game playing, task completion, etc.)
- What is a "session" or "run"? (one forecast, one conversation, one game, one task)

### 2. Ground Truth & Success Metrics
- How do you know if the agent did well?
  - **External ground truth**: Outcomes that resolve later (predictions, game wins, task success)
  - **Human feedback**: Ratings, corrections, preferences
  - **Proxy metrics**: Engagement time, task completion, coherence scores
  - **Self-assessment**: Agent's own meta-reflection quality
  - **No clear ground truth**: Focus on process quality and trace analysis

### 3. What to Track
- What outputs should be saved per session?
- What metrics matter? (accuracy, cost, time, tool usage, user satisfaction)
- What trace data is valuable? (reasoning, tool calls, intermediate states)

### 4. Feedback Sources
- Where does feedback come from?
  - Resolution/outcome data
  - User ratings or corrections
  - Comparison against baselines
  - Expert review
  - Automated quality checks

### 5. Task Format
- How are tasks provided to the agent? (free text, IDs, files, API calls)
- Should the `loop` CLI command batch-process them?
- What does auto-commit look like for this domain?

## Interviewing Style

Use AskUserQuestion extensively — don't make assumptions about the domain. Ask open-ended questions first, then drill into specifics. Example questions (adapt based on context):

- "What does your agent do and what does a single session look like?"
- "How do you know if the agent did well? Is there ground truth that resolves later?"
- "What metrics matter most to you?"
- "How are tasks provided — free text, IDs, files, API calls?"
- "Should results auto-commit after each session?"
- "What tools or APIs will the agent need?"
- "Should data commits (session results, scores) auto-commit? To main directly, or a dedicated data branch?"

Let the conversation flow naturally. The goal is to understand the domain well enough to customize the template files below.

## Phase 2: Generate Scaffolding

Based on the answers, generate or modify:

### 1. `src/loop/agent/models.py`
Customize AgentOutput for the domain:
- Add domain-specific fields (probability, move, response, etc.)
- Add domain-specific columns to `src/loop/lib/scoring.py` CSV_COLUMNS

### 2. `src/loop/agent/prompts.py`
Update the system prompt template for the domain.

### 3. `src/loop/agent/subagents.py`
Create domain-appropriate subagents (researcher, analyzer, etc.)

### 4. `src/loop/environment/cli/__main__.py`
Customize the CLI for the domain's task format:
- Update the `loop` command to accept domain-specific task inputs
- Customize `_commit_results()` message format (e.g., `data(forecasts):` instead of `data(sessions):`)
- Configure auto-commit behavior: enable/disable by default, target branch (main for data-only commits, or a dedicated branch)
- Add domain-specific CLI commands if needed

### 5. `src/loop/version.py`
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

## Phase 3: Verify Setup

After generating files:

1. Run `uv run pyright` to check types
2. Run `uv run ruff check .` to check lint
3. Run `uv run python -m loop.environment.cli --help` to verify CLI
4. Verify the feedback loop command references the right scripts
5. Check that CLAUDE.md accurately describes the domain

## After Initialization

Once the scaffolding is generated, guide the user to:

1. Run a few sessions: `uv run python -m loop.environment.cli loop "task1" "task2"`
2. Review traces in `notes/traces/`
3. Check scores in `notes/scores.csv`
4. Use `/loop:feedback-loop` to analyze and improve
5. Iterate on the feedback collection as patterns emerge

## Key Files to Customize

- `src/loop/agent/models.py` — Output schemas (AgentOutput, SessionResult)
- `src/loop/agent/subagents.py` — Specialized subagents
- `src/loop/agent/tool_policy.py` — Tool availability and MCP servers
- `src/loop/agent/core.py` — Options building and orchestration
- `src/loop/agent/prompts.py` — System prompt templates
- `src/loop/environment/cli/__main__.py` — CLI with loop + auto-commit
- `src/loop/lib/scoring.py` — CSV columns and score row building
- `src/loop/version.py` — Agent version tracking
- `.claude/plugins/loop/scripts/feedback_collect.py` — Feedback collection
