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

## Phase 2: Generate Scaffolding

Based on the answers, generate or modify:

### 1. `feedback_collect.py`
The main feedback collection script. Template:

```python
#!/usr/bin/env python3
"""Collect feedback data from {DOMAIN} sessions.

Customized for: {DESCRIPTION}
Ground truth type: {GROUND_TRUTH_TYPE}
Key metrics: {METRICS}
"""

import json
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

# TODO: Customize these paths for your domain
SESSIONS_PATH = Path("./notes/sessions")
FEEDBACK_PATH = Path("./notes/feedback_loop")
TRACES_PATH = Path("./notes/traces")


class SessionResult(BaseModel):
    """A session matched with its outcome/feedback."""
    session_id: str
    timestamp: str
    # TODO: Add domain-specific fields
    # outcome: ...
    # metrics: ...


class FeedbackMetrics(BaseModel):
    """Aggregated metrics from sessions."""
    collection_timestamp: str
    total_sessions: int
    sessions_with_feedback: int
    # TODO: Add domain-specific aggregate metrics


def collect_sessions() -> list[dict]:
    """Load all session data."""
    sessions = []
    if not SESSIONS_PATH.exists():
        return sessions

    for session_dir in SESSIONS_PATH.iterdir():
        if not session_dir.is_dir():
            continue
        # TODO: Load session data for your domain
        pass

    return sessions


def match_feedback(sessions: list[dict]) -> list[SessionResult]:
    """Match sessions to their feedback/outcomes."""
    results = []
    # TODO: Implement feedback matching for your domain
    return results


def compute_metrics(results: list[SessionResult]) -> FeedbackMetrics:
    """Compute aggregate metrics."""
    # TODO: Implement domain-specific metrics
    return FeedbackMetrics(
        collection_timestamp=datetime.now().isoformat(),
        total_sessions=len(results),
        sessions_with_feedback=0,
    )


def main():
    """Collect and report feedback."""
    print("Collecting feedback...")
    sessions = collect_sessions()
    results = match_feedback(sessions)
    metrics = compute_metrics(results)

    # Save metrics
    FEEDBACK_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = FEEDBACK_PATH / f"{timestamp}_metrics.json"
    output_file.write_text(metrics.model_dump_json(indent=2))
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
```

### 2. `trace_analysis.py`
For inspecting reasoning traces:

```python
#!/usr/bin/env python3
"""Analyze reasoning traces from sessions."""

import json
from pathlib import Path
import typer

app = typer.Typer(help="Analyze session traces")
TRACES_PATH = Path("./notes/traces")


@app.command("show")
def show(session_id: str):
    """Show trace for a session."""
    # TODO: Implement trace loading for your domain
    pass


@app.command("search")
def search(pattern: str):
    """Search traces for a pattern."""
    # TODO: Implement trace search
    pass


@app.command("errors")
def errors():
    """Show sessions with errors."""
    # TODO: Implement error extraction
    pass


if __name__ == "__main__":
    app()
```

### 3. Update `CLAUDE.md`
Add domain-specific sections:
- Project overview with domain description
- Commands specific to the domain
- Metrics and feedback collection instructions

### 4. Update `feedback-loop.md`
Customize the feedback loop command for the domain's specific:
- Ground truth type
- Metrics to analyze
- Trace inspection approach

## Phase 3: Verify Setup

After generating files:

1. Run `uv run python .claude/plugins/loop/scripts/feedback_collect.py --help`
2. Verify the feedback loop command references the right scripts
3. Check that CLAUDE.md accurately describes the domain

## Questions Template

```
1. What does your agent do?
   - Forecasting/prediction
   - Coaching/assistance
   - Game playing
   - Task completion
   - Content generation
   - Other: ___

2. What is a "session"?
   - One question/prediction
   - One conversation
   - One game
   - One task
   - Other: ___

3. How do you measure success?
   - External outcomes (ground truth)
   - Human ratings
   - Task completion
   - Engagement metrics
   - Self-assessment
   - No clear metric (process-focused)

4. What should be tracked per session?
   - Final output
   - Reasoning trace
   - Tool calls
   - Time/cost
   - User feedback
   - All of the above

5. Where does feedback come from?
   - Automated resolution
   - User ratings
   - Expert review
   - Comparison to baseline
   - Self-reflection
```

## After Initialization

Once the scaffolding is generated, guide the user to:

1. Customize `src/loop/agent/models.py` for their output schema
2. Build domain logic in `src/loop/environment/`
3. Run a few sessions to generate data
4. Use `/loop:feedback-loop` to analyze and improve
5. Iterate on the feedback collection as patterns emerge

Remember: The scaffolding should be easy to modify. Don't over-engineer the initial setup - it's meant to evolve through the feedback loop itself.

## Key Files to Customize

- `src/loop/agent/models.py` — Output schemas (AgentOutput, SessionResult)
- `src/loop/agent/subagents.py` — Specialized subagents
- `src/loop/agent/tool_policy.py` — Tool availability and MCP servers
- `src/loop/agent/core.py` — System prompt and orchestration
- `src/loop/environment/client.py` — User interaction and game logic
- `.claude/plugins/loop/scripts/feedback_collect.py` — Feedback collection
