---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, Task, WebSearch, AskUserQuestion
description: Analyze sessions and improve the agent based on feedback and process quality
---

# Feedback Loop: Three Levels of Analysis

The feedback loop operates at three levels. Be clear about which level you're working at:

1. **Object Level** - The agent itself: tools, capabilities, data access, runtime behavior
2. **Meta Level** - The agent's self-assessment: meta-prompts, reflection templates, metrics emission, what the agent tracks about itself
3. **Meta-Meta Level** - This feedback loop process: the scripts, the analysis methods, this document itself

**Clarification**:
- Object level = "How can the agent perform better?" (tools, APIs, reasoning)
- Meta level = "How can the agent track its own performance better?" (meta-reflection prompts, metrics formats)
- Meta-meta level = "How can this feedback loop work better?" (feedback_collect.py, this document, analysis workflows)

**IMPORTANT: Every feedback loop session should span all three levels thoroughly.**

Don't stop after finding object-level improvements. Ask yourself:
- Did I check if the agent's self-tracking is sufficient? (meta)
- Did I update this document with what I learned? (meta-meta)
- Are there scripts that would make next session easier? (meta-meta)

A good feedback loop session produces changes at multiple levels. If you only made object-level changes, you probably skipped the reflection phases.

## Guiding Principle: The Bitter Lesson

Give the agent MORE capabilities and tools rather than MORE prescriptive rules.

| Prefer | Over |
|--------|------|
| Tools that provide data | Prompt rules that constrain behavior |
| General principles | Specific pattern patches |
| State/context via tools | F-string prompt engineering |
| Subagents for specialized work | Complex pipelines in main agent |

**The test**: Would this change still help if the domain shifted completely? General principles yes, specific patches no.

**Clarification**: The bitter lesson does NOT mean never modifying prompts. It's fine to add:
- General guidance for categories of tasks
- Principles that help reasoning
- Structural guidance for output formats

What to AVOID:
- Specific numeric patches ("always subtract 10% from initial estimate")
- Rules that hard-code observations from specific sessions
- Prescriptive formulas that will become outdated

Keep the system prompt fresh - periodically review and remove guidance that no longer applies.

## Phase 1: Ground Truth - What Actually Matters

The ONLY true ground truth is **outcomes**. Everything else is proxy signal.

### 1a. Collect Feedback Data

```bash
# Customize this for your domain
uv run python .claude/plugins/loop/scripts/feedback_collect.py --all-time
```

**If you have outcome data**: Focus on accuracy/success metrics. This is the REAL signal.
- Which sessions performed worst? Read their traces.
- Are there systematic patterns in errors?

**If you have NO outcomes yet**: You're flying blind on accuracy. Focus on:
- Process quality (is the agent reasoning well?)
- Tool failures (what's blocking the agent?)
- Do NOT treat proxy metrics as evidence of error without validation

### 1b. Understand Your Feedback Sources

Different domains have different ground truth:

| Domain | Ground Truth | Proxy Signal |
|--------|-------------|--------------|
| Forecasting | Resolution outcomes | Community prediction |
| Coaching | User outcomes/ratings | Session engagement |
| Game playing | Win/loss | Move quality scores |
| Task completion | Task success | Time to completion |
| Content generation | User satisfaction | Automated quality scores |

**Be honest about what you can and cannot measure.**

## Phase 2: Object Level - Read Traces Deeply

**This is the most important phase.** Do not skip to aggregate patterns.

### 2a. Read Full Reasoning Traces

Traces show exactly what the agent thought and did. They are more detailed than any summary.

```bash
# List sessions
ls notes/traces/

# Read a specific trace
cat notes/traces/<session_id>/*.md
```

### 2b. Sample 5-10 Sessions

Pick a sample including:
- Sessions with poor outcomes (if available)
- Sessions where tools failed
- Sessions across different task types

For each, ask:
1. **Is the reasoning sound?** Does the logic follow from the evidence?
2. **What tools worked?** What provided high-value information?
3. **What tools failed?** What blocked progress?
4. **What does the agent say it needs?** Explicit capability requests

### 2c. Extract Tool Failures

```bash
# Tool failures mentioned in traces/reflections
grep -rh "failed\|error\|Error\|didn't work\|couldn't\|blocked" notes/traces/*.md | sort | uniq -c | sort -rn | head -20
```

Common patterns:
- API returns errors → Fix or add fallback
- Tool exists but agent doesn't use it → Improve discoverability
- Tool output is unhelpful → Improve tool design

### 2d. Extract Capability Requests

```bash
# What the agent explicitly says it needs
grep -rh "would be useful\|would have helped\|would benefit\|wish I had\|tool that" notes/traces/*.md | head -20
```

**Trust these requests.** The agent knows what it needs. Build the tools it asks for.

### 2e. Evaluate Reasoning Quality

For sessions with poor outcomes, ask:
1. Is the agent's evidence valid?
2. Is the logic sound?
3. Are there gaps in the analysis?
4. Would a different approach be MORE justified by the evidence?

**If reasoning is sound**: The failure may be due to genuine uncertainty or missing information.
**If reasoning is flawed**: Identify the specific failure. Is it a capability gap or a reasoning error?

## Phase 3: Meta Level - Analysis Process Quality

Evaluate whether this feedback loop is finding the right things to improve.

### 3a. Did the Analysis Surface Actionable Insights?

Ask yourself:
- Did I find specific tools to fix or build?
- Did I identify concrete capability gaps?
- Did the analysis lead to clear next steps?

If the analysis felt circular or unproductive, the meta-process needs improvement.

### 3b. Evaluate Tracking Data Quality

Check if the data we collect is sufficient for analysis:
- Are sessions linked to their reasoning traces?
- Can we correlate tool usage with session quality?
- Do we have outcome data to evaluate accuracy?

```bash
# Check what tracking data we have
uv run python .claude/plugins/loop/scripts/trace_analysis.py list
```

### 3c. Identify Missing Data

Common gaps:
- **No outcome data** → Can't evaluate accuracy, only process
- **No tool-to-session linkage** → Can't identify which tools help
- **No category tagging** → Can't identify patterns by type

If you find gaps, add tracking in Phase 4.

## Phase 4: Implement Changes (Bitter Lesson Order)

### Priority 1: Fix Failing Tools

If a tool fails repeatedly, fix it or add an alternative.

### Priority 2: Build Requested Tools

What did the agent explicitly request? **Don't just build—discuss with the user first.**

For each capability gap found in traces:

1. **Quantify**: How many sessions mentioned this need?
2. **Research**: What APIs or approaches exist?
3. **Ask the user**: Use `AskUserQuestion` to present options and recommendations

### Priority 3: Improve Subagents

If subagents aren't used:
- Are they providing unique value?
- Are they too expensive (time/compute)?
- Should they be lighter/faster?

### Priority 4: Simplify Prompts (Not Add Rules)

Prompt changes should:
- ADD general principles that help across domains
- REMOVE prescriptive rules that add complexity
- PREFER "use tool X for Y" over "when pattern P, do Q"

**Do NOT add**:
- Specific rules for specific task types
- Numeric adjustments ("always add 10% margin")
- Patches for observed patterns

## Phase 5: Meta-Meta Level - Improve This Document

This phase is about improving the feedback loop infrastructure itself.

### 5a. Was This Document Helpful?

Ask:
- Did the phases guide you to useful insights?
- Was any guidance outdated or confusing?
- Did you have to improvise steps not documented here?

If yes to any, update this document NOW before you forget.

### 5b. Build Missing Scripts

If you found yourself doing repetitive analysis, automate it:

```bash
# Scripts that should exist:
uv run python .claude/plugins/loop/scripts/feedback_collect.py --help
uv run python .claude/plugins/loop/scripts/trace_analysis.py --help
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py --help
```

If you need a script that doesn't exist, create it and document it in CLAUDE.md.

### 5c. Improve Data Collection

If the feedback loop lacked data, fix the source:
- Add fields to session output schema
- Update the agent to emit more tracking data
- Add scripts to collect missing metrics

### 5d. Update This Document

Every session should leave this document better:
- Remove outdated guidance
- Add new scripts to the reference section
- Clarify confusing terminology
- Add examples from actual analysis

## Anti-Patterns to Avoid

### DON'T: Patch prompts for observed patterns
❌ "When doing X, always subtract 10%"
❌ "For Y tasks, cap confidence at 70%"
✅ Build tool that provides historical calibration data
✅ Add general principle about uncertainty

### DON'T: Over-rely on proxy metrics
❌ "Large divergence from baseline means we're wrong"
✅ Wait for outcome data to know if divergence correlates with error
✅ Use proxy metrics to understand WHERE reasoning differs, not WHETHER it's wrong

### DON'T: Add rules the agent can't act on
❌ "Adjust based on X" (if agent can't see X)
✅ Provide tools that give the agent actionable information

### DON'T: Skip reading traces
❌ Jump to aggregate statistics
✅ Read 5-10 traces deeply first
✅ Understand what actually happened in individual sessions

## Documentation Template

Write to `notes/feedback_loop/<timestamp>_analysis.md`:

```markdown
# Feedback Loop Analysis: YYYY-MM-DD

## Ground Truth Status
- Sessions with outcomes: N
- Average success metric: X.XX (or "none yet - process analysis only")

## Object-Level Findings

### Tool Failures
| Tool | Failure | Count | Fix |
|------|---------|-------|-----|
| ... | ... | N | ... |

### Agent Capability Requests
- "Would benefit from X" → [action taken]
- "Tool Y failed" → [action taken]

### Reasoning Quality Assessment
- [For 3-5 sessions, brief assessment of reasoning soundness]

## Meta-Level Findings (Analysis Process)

### Was This Analysis Productive?
- Did it surface actionable insights? [yes/no]
- What data was missing?
- What would have made analysis easier?

## Meta-Meta Findings (Feedback Loop Infrastructure)

### Updates to This Document
- [Changes made to feedback-loop.md]

### Scripts Created/Updated
- [New scripts added]

### Data Collection Improvements
- [Changes to tracking, metrics, etc.]

## Changes Made
| Level | Change | Rationale |
|-------|--------|-----------|
| Object | Added X tool | Agent requested it in N traces |
| Meta | Improved analysis queries | Was missing Y data |
| Meta-Meta | Updated feedback-loop.md | Clarified Z section |
```

## Scripts Reference

```bash
# Collect feedback data
uv run python .claude/plugins/loop/scripts/feedback_collect.py --all-time

# Analyze traces
uv run python .claude/plugins/loop/scripts/trace_analysis.py show <session_id>
uv run python .claude/plugins/loop/scripts/trace_analysis.py search "error"
uv run python .claude/plugins/loop/scripts/trace_analysis.py errors

# Aggregate metrics
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py summary
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py tools
uv run python .claude/plugins/loop/scripts/aggregate_metrics.py by-type
```

## Key Questions to Answer Each Session

1. **Do we have outcome data?** If no, focus on process not accuracy.
2. **What's our success rate?** This is the REAL metric (when available).
3. **What tools fail repeatedly?** Fix or replace them.
4. **What does the agent say it needs?** Trust and provide.
5. **Is the agent's reasoning sound?** Read traces deeply to find out.
6. **What would make this process better?** Update this document.
