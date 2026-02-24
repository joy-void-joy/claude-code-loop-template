---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, Task, WebSearch, AskUserQuestion
description: Analyze sessions and improve the agent based on feedback and process quality
argument-hint: [optional: paste a trace, reflection, or output for single-trace analysis]
---

# Feedback Loop: Three Levels of Analysis

## Single-Trace Mode

**If the user pasted trace content as an argument**: $ARGUMENTS

When trace content is provided, run a focused single-trace deep analysis instead of the full multi-session feedback loop. This mode analyzes one session in depth for tool use quality, reasoning soundness, workflow effectiveness, and pipeline health.

### Step 1: Orient

Read the pasted content and establish context:

- **Task**: What was the agent trying to do?
- **Agent version**: From metadata or version directory path
- **Duration**: How long did the session take?
- **Outcome**: What did the agent produce?

State this context in 3-4 lines at the top of your report.

### Step 2: Tool Use Audit

Go through every tool call in the trace:

**2a. Tool Call Inventory** — List every tool call with: tool name, what the agent was trying to learn, whether it succeeded, whether the result was useful.

**2b. Tool Errors and Failures** — For each failed tool call: (1) what happened (quote the error), (2) why it failed (read the relevant tool in `src/lup/agent/tools/` to understand the failure mode), (3) was the agent's recovery reasonable, (4) is this a known issue or new bug (grep for the error pattern).

**2c. Subtle Tool Bugs** — Cases where a tool *succeeded* but returned misleading or incomplete data. Search results that missed obvious sources, API data that was stale, tool results the agent misinterpreted.

**2d. Missing Tool Calls** — Tools the agent *should* have called but didn't. Check against available tools in `src/lup/agent/tools/`.

### Step 3: Workflow Assessment

**3a. Information Gathering** — Did the agent gather enough evidence? Triangulate across sources? Front-load research or jump to conclusions early?

**3b. Structured Reasoning** — Did the agent decompose the problem? Identify and weigh uncertainties? Consider base rates or priors?

**3c. Self-Correction** — Did the agent update its view on new evidence? Flag its own uncertainty honestly?

**3d. Efficiency** — Wasted tool calls? Proportional effort on important vs. trivial factors?

### Step 4: Pipeline Health

System-level problems separate from the agent's reasoning:

- MCP connection issues (tools timing out, empty results)
- Token/context pressure (reasoning truncated, limits hit)
- Prompt issues (agent confused by instructions, didn't follow system prompt)
- Hook behavior (permission hooks blocking valid operations)

When you spot a pipeline issue, read the relevant source code (`src/lup/agent/core.py`, `src/lup/agent/prompts.py`, etc.).

### Step 5: Report

```markdown
## Trace Review: [Task Description]

**Context**: [task type] | [agent version] | [duration] | [outcome]

### Tool Use
- **Calls**: N total (N succeeded, N failed, N low-value)
- **Errors**: [list each with brief explanation]
- **Subtle issues**: [tools that succeeded but returned questionable data]
- **Missing**: [tools the agent should have used]

### Workflow
- **Information gathering**: [adequate / rushed / thorough but unfocused]
- **Structure**: [well-decomposed / ad-hoc / overly complex]
- **Self-correction**: [evidence of updating views, or lack thereof]
- **Efficiency**: [good / wasted N calls on X]

### Reasoning
- **Strengths**: [what the agent got right]
- **Weaknesses**: [logical gaps, missed evidence, calibration issues]

### Pipeline
- **Issues found**: [system-level problems, or "none"]
- **Source code investigation**: [what was found in src/ for each issue]

### Bugs Found
[For each bug — what happened, which source file, what the fix would be]

### Actionable Takeaways
1. [Most important finding — what to fix or improve]
2. [Second priority]
3. [Third priority]
```

### Rules

- **Start from the trace.** Read every line of the pasted content before reaching for source code.
- **Dig into source code only when the trace gives you a reason.** A tool error, a suspicious result, a pipeline hiccup — these warrant reading `src/`. Don't read source code preemptively.
- **Quote the trace.** When you identify an issue, quote the exact lines that show it.
- **Be specific about bugs.** "The search tool had issues" is useless. "web_search returned 0 results for query X — checking src/lup/agent/tools/example.py, the query is passed without filtering" is useful.
- **Distinguish agent issues from system issues.** A bad search query is the agent's fault. A tool returning an error is a pipeline issue.
- **Ask when the trace is ambiguous.** Use AskUserQuestion rather than guessing.

**After completing single-trace analysis, stop.** Do not proceed to the full multi-session feedback loop below unless the user asks.

---

## Full Multi-Session Feedback Loop

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

**Tools are the highest-leverage change you can make.** A tool that provides the right data at the right time is worth more than any amount of prompt engineering. When the agent struggles, the answer is almost always a missing tool — not a missing prompt paragraph.

| Prefer                         | Over                                 |
| ------------------------------ | ------------------------------------ |
| Tools that provide data        | Prompt rules that constrain behavior |
| General principles             | Specific pattern patches             |
| State/context via tools        | F-string prompt engineering          |
| Subagents for specialized work | Complex pipelines in main agent      |

**The test**: Would this change still help if the domain shifted completely? General principles yes, specific patches no.

**Prompts rot; tools don't.** Listing tools in the prompt creates two sources of truth that drift apart as tools change. The agent discovers tools through their descriptions, so putting tool knowledge in the description (not the prompt) keeps it accurate.

**The description is the contract.** When the agent misuses a tool or ignores one it should use, the description is usually the problem. A good description answers what the tool does, when to reach for it, and why it exists — so the agent can match its situation to the tool without prompt-level instructions.

**Clarification**: The bitter lesson does NOT mean never modifying prompts. It's fine to add:

- General guidance for categories of tasks
- Principles that help reasoning
- Structural guidance for output formats

What to AVOID:

- Specific numeric patches ("always subtract 10% from initial estimate")
- Rules that hard-code observations from specific sessions
- Listing tools in the prompt (creates a second source of truth that drifts)
- Terse tool descriptions (the agent can't self-select tools it doesn't understand)

Keep the system prompt fresh - periodically review and remove guidance that no longer applies.

## Phase 0: Read Previous Analysis

**Before collecting any data, read what was already done.** This prevents double-fixing.

```bash
# Check what the last session found and changed
ls notes/feedback_loop/
cat notes/feedback_loop/*_analysis.md | tail -50
```

Read the most recent `*_analysis.md` file. Understand:

- What problems were already identified and fixed
- What sessions were already analyzed
- What changes were already made

## Phase 1: Ground Truth - What Actually Matters

The ONLY true ground truth is **outcomes**. Everything else is proxy signal.

### 1a. Collect Feedback Data

```bash
# Check current agent version
grep AGENT_VERSION src/lup/version.py

# Customize this for your domain
uv run lup-devtools feedback collect --all-time
```

**Always scope analysis to the current agent version.** Different versions have different prompts, tools, and subagent configurations. Mixing data across versions produces meaningless aggregate statistics. Devtools commands auto-scope to the current version (see [Version Scoping](#version-scoping) above).

**If you have outcome data**: Focus on accuracy/success metrics. This is the REAL signal.

- Which sessions performed worst? Read their traces.
- Are there systematic patterns in errors?
- **Compare across versions** to see if recent changes helped or hurt.

**If you have NO outcomes yet**: You're flying blind on accuracy. Focus on:

- Process quality (is the agent reasoning well?)
- Tool failures (what's blocking the agent?)
- Do NOT treat proxy metrics as evidence of error without validation

### 1b. Understand Your Feedback Sources

Different domains have different ground truth:

| Domain             | Ground Truth          | Proxy Signal             |
| ------------------ | --------------------- | ------------------------ |
| Forecasting        | Resolution outcomes   | Community prediction     |
| Coaching           | User outcomes/ratings | Session engagement       |
| Game playing       | Win/loss              | Move quality scores      |
| Task completion    | Task success          | Time to completion       |
| Content generation | User satisfaction     | Automated quality scores |

**Be honest about what you can and cannot measure.**

## Phase 2: Object Level - Read Traces Deeply

**This is the most important phase.** Do not skip to aggregate patterns.

### Version Scoping

All devtools commands **default to the current AGENT_VERSION** with progressive semver
fallback (exact → X.Y.* → X.* → all) when the current version has insufficient data.
You do NOT need to manually pass `--version` — commands auto-scope.

**For learning phases** that need data from older versions, use `--all-versions`:
```bash
uv run lup-devtools metrics summary --all-versions
uv run lup-devtools trace errors --all-versions
```

**Scoping examples:**
```bash
# Current version (default) — for diagnostics and current performance
uv run lup-devtools metrics summary
uv run lup-devtools trace errors

# All versions — for learning from historical sessions
uv run lup-devtools metrics tools --all-versions
uv run lup-devtools feedback collect --all-versions
```

**Use devtools to find best/worst sessions for deep trace reading:**

```bash
# Session metrics summary (auto-scoped to current version)
uv run lup-devtools metrics summary
uv run lup-devtools metrics errors
```

### 2a. Launch Trace Explorer (Subagent)

**Do NOT read traces directly in this conversation.** Traces consume many lines each and will
exhaust the context window before you reach later phases. Instead, launch the `trace-explorer`
subagent which reads traces in its own context and returns a compact pattern report.

**Select which traces to analyze:**

```bash
# List available traces
uv run lup-devtools trace list

# Find sessions with errors
uv run lup-devtools trace errors

# Extract capability requests
uv run lup-devtools trace capabilities
```

**Launch the trace explorer:**

```
Task(subagent_type="lup:trace-explorer", prompt="""
Analyze traces for these session IDs: [list of 5-15 IDs]

Context:
- Current agent version: [X.Y.Z]
- Focus areas: [e.g., "tool failures", "reasoning quality", "capability gaps"]
- Known issues from Phase 1: [brief summary of findings]

Return the standard pattern report.
""")
```

**What to include in the prompt:**

- Session IDs to analyze (from `lup-devtools metrics errors`, or all recent sessions)
- Current agent version (devtools auto-scope, but state it for the explorer)
- Any specific focus areas from Phase 1 findings
- Known issues from the previous feedback session (Phase 0)

**What you get back:**

- Tool failure patterns (aggregated across all traces)
- Capability requests (what the agent asked for)
- Reasoning patterns and quality issues
- Tool usage patterns (high-value vs low-value tools)
- 2-3 specific traces worth reading in full (outliers or interesting cases)

**Other subagents for deeper analysis:**

- **Version reviewer**: For a holistic assessment of a single past version (especially before prompt rewrites), use:
  ```
  Task(subagent_type="lup:version-reviewer", prompt="Review version [X.Y.Z]")
  ```
- **Version explorer**: For quick file retrieval and diffs across versions (e.g., "fetch me the prompt at v0.3" or "compare v0.3 and v1.0 prompts"):
  ```
  Task(subagent_type="lup:version-explorer", prompt="Compare v0.3.0 and v1.0.0")
  ```

The trace explorer finds cross-cutting patterns; the version reviewer explains why those patterns exist by connecting them to the prompt; the version explorer retrieves and diffs the actual code. You can run all three — they serve complementary purposes.

### 2b. Deep-Dive on Flagged Traces (Optional)

The trace explorer flags 2-3 traces worth reading fully. **Only read these if the pattern
report raises specific questions** that need full-trace context to answer.

If you do read a trace, use the trace analysis script and read it with a
specific question in mind — don't just browse.

### 2c. Evaluate Findings

Based on the trace explorer's pattern report:

1. **Tool failures**: Which tools fail most? Are they fixable or should we add alternatives?
2. **Capability requests**: What does the agent say it needs? Trust these requests.
3. **Reasoning quality**: Are there systematic reasoning errors, or just individual misjudgments?
4. **Tool value**: Are expensive tools providing proportional value?

**If reasoning is sound**: The failure may be due to genuine uncertainty or missing information.
**If reasoning is systematically flawed**: Identify whether it's a capability gap or a prompt issue.

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
uv run lup-devtools trace list
```

### 3c. Identify Missing Data

Common gaps:

- **No outcome data** → Can't evaluate accuracy, only process
- **No tool-to-session linkage** → Can't identify which tools help
- **No category tagging** → Can't identify patterns by type

If you find gaps, add tracking in Phase 4.

## Phase 4: Implement Changes (Bitter Lesson Order)

**Tools are the highest-leverage change.** The priority order below reflects this — fix and build tools first, simplify prompts last.

**Log every change** in the analysis document (see Documentation Template). The next feedback session reads this (Phase 0) to avoid re-deriving the same improvements. Be specific: "Added X to Y because Z" — not just "improved prompts."

### Priority 0: Evaluate Prompt Health

Before patching individual issues, assess whether the system prompt needs a structural
rewrite rather than another incremental patch.

**When to rewrite vs patch:**

A full rewrite is warranted when:

- Sections read as addendums rather than integrated guidance (conditional exceptions, "if X fails, do Y" patches)
- The same task type has been patched 3+ times across sessions
- Best-performing traces succeed despite the prompt, not because of it
- Worst-performing traces fail because the prompt's decision tree doesn't match how the agent should think
- The prompt has grown >20% since the last rewrite without corresponding improvement

**How to do a principled rewrite:**

1. **Study the best-performing traces.** Read the full reasoning for the top 5-10 sessions. What patterns do they follow? What decisions led to success?
2. **Study the worst-performing traces.** Same process for the bottom 5-10. What went wrong — capability gap or reasoning error the prompt could have prevented?
3. **Read the full current prompt** (`src/lup/agent/prompts.py`). Identify sections that feel patched, redundant, or irrelevant.
4. **Draft from scratch.** Write the prompt as you would if starting today with all accumulated knowledge. Don't copy-paste — rewrite each section from first principles, incorporating the patterns from best traces.
5. **Ensure monolithic coherence.** The result must read as a single authored document — no references to "previous behavior," no "Exception:" patches, no "Note: as of version X."

**When NOT to rewrite:**

- If you found only 1-2 clear bugs or gaps, a targeted patch is better
- If the prompt's structure is sound and only needs a new principle or tool reference
- If there isn't enough data (< 20 sessions with outcomes) to identify structural issues

### Priority 1: Fix Failing Tools

If a tool fails repeatedly, fix it or add an alternative. A broken tool is worse than no tool — it wastes tokens and teaches the agent to avoid it.

### Priority 2: Build Requested Tools

What did the agent explicitly request? **Don't just build—discuss with the user first.**

For each capability gap found in traces:

1. **Quantify**: How many sessions mentioned this need?
2. **Research**: What APIs or approaches exist?
3. **Ask the user**: Use `AskUserQuestion` to present options and recommendations

Good tool descriptions answer what/when/why — this helps the agent self-select the right tool without prompt-level instructions.

### Priority 3: Improve Tool Descriptions

Before changing prompts, check if the issue is a tool description problem:

- Is the agent using the wrong tool? → Clarify the "when" in the description.
- Is the agent not using a tool at all? → Add stronger "when to use" triggers.
- Is the agent misinterpreting results? → Document the return format.

### Priority 4: Improve Subagents

If subagents aren't used:

- Are they providing unique value?
- Are they too expensive (time/compute)?
- Should they be lighter/faster?

### Priority 5: Simplify Prompts (Not Add Rules)

For incremental prompt changes (when Priority 0 determined a full rewrite isn't needed):

- ADD general principles that help across domains
- REMOVE prescriptive rules that add complexity
- PREFER "use tool X for Y" over "when pattern P, do Q"

**Do NOT add**:

- Specific rules for specific task types (over-fitted, won't generalize)
- Numeric adjustments ("always add 10% margin") (will become stale)
- Patches for observed patterns (treat symptoms, not causes)
- Conditional exceptions that reference specific failure modes

**Track patch count.** If you add a patch this session, count how many patches have been
added since the last rewrite. If the count exceeds 3, flag it in your analysis — the next
session should evaluate a full rewrite (Priority 0).

### Version Bumps

After implementing changes that affect agent behavior, **always bump the version** using `/lup:bump`:

- **Patch (0.x.Y)**: Bug fixes, tool fixes, config tweaks. Default when unsure.
- **Minor (0.X.0)**: Prompt changes, new tools, subagent modifications.
- **Major (X.0.0)**: Architecture changes (new LLM, new framework, major restructuring).

Data-only or infrastructure changes (scripts, feedback-loop docs) don't need a bump.

## Phase 5: Meta-Meta Level - Improve This Document

This phase is about improving the feedback loop infrastructure itself.

### 5a. Was This Document Helpful?

Ask:

- Did the phases guide you to useful insights?
- Was any guidance outdated or confusing?
- Did you have to improvise steps not documented here?

If yes to any, update this document NOW before you forget.

### 5b. Build Missing Scripts

If you found yourself doing repetitive analysis, automate it by adding a command to `src/lup/devtools/`. Use `uv run lup-devtools --help` to see existing commands.

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
❌ Adding "Exception:" clauses to existing rules
❌ "If X fails, do Y" conditional patches
✅ Build tool that provides historical calibration data
✅ Add general principle about uncertainty
✅ When patches accumulate, rewrite the section from scratch (Priority 0)

### DON'T: Over-rely on proxy metrics

❌ "Large divergence from baseline means we're wrong"
✅ Wait for outcome data to know if divergence correlates with error
✅ Use proxy metrics to understand WHERE reasoning differs, not WHETHER it's wrong

### DON'T: Add rules the agent can't act on

❌ "Adjust based on X" (if agent can't see X)
✅ Provide tools that give the agent actionable information

### DON'T: List tools in prompts or write terse descriptions

❌ "## Tools Available\n- **WebSearch**: Search the web"
❌ Tool description: "Search for information"
✅ Let the agent discover tools through comprehensive descriptions
✅ Tool description: "Search for X using Y. Use when Z. Exists because W. Returns {format}."

### DON'T: Skip reading traces

❌ Jump to aggregate statistics
✅ Read 5-10 traces deeply first
✅ Understand what actually happened in individual sessions

## Documentation Template

Write to `notes/feedback_loop/<timestamp>_analysis.md`:

```markdown
# Feedback Loop Analysis: YYYY-MM-DD

## Ground Truth Status

- Agent version analyzed: X.Y.Z
- Sessions with outcomes: N
- Average success metric: X.XX (or "none yet - process analysis only")

## Object-Level Findings

### Tool Failures

| Tool | Failure | Count | Fix |
| ---- | ------- | ----- | --- |
| ...  | ...     | N     | ... |

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

| Level     | Change                    | Rationale                      |
| --------- | ------------------------- | ------------------------------ |
| Object    | Added X tool              | Agent requested it in N traces |
| Meta      | Improved analysis queries | Was missing Y data             |
| Meta-Meta | Updated feedback-loop.md  | Clarified Z section            |

## Evaluation Queue

uv run python -m lup.environment.cli loop <session commands>
```

## Scripts Reference

```bash
# Collect feedback data
uv run lup-devtools feedback collect --all-time

# Analyze traces
uv run lup-devtools trace show <session_id>
uv run lup-devtools trace search "error"
uv run lup-devtools trace errors

# Aggregate metrics
uv run lup-devtools metrics summary
uv run lup-devtools metrics tools
uv run lup-devtools metrics errors
```

## Periodic Maintenance

Every few feedback loop sessions, take time to:

1. **Reread this entire document** - Is it still accurate? Remove outdated guidance.
2. **Prompt health audit** - Read the entire system prompt (`src/lup/agent/prompts.py`) with fresh eyes. Does it read as a coherent, monolithic document? Are there visible patches? Would a new reader understand the decision tree? If not, trigger a rewrite (Phase 4, Priority 0).
3. **Refactor scripts** - Consolidate duplicate functionality in feedback loop scripts, improve error handling.
4. **Clean up notes/** - Archive old analysis files, ensure naming is consistent.
5. **Update CLAUDE.md** - Sync any learnings that should persist to the main project docs.

## Key Questions to Answer Each Session

1. **What AGENT_VERSION am I analyzing?** Filter ALL data by version. Do not mix versions.
2. **Do we have outcome data?** If no, focus on process not accuracy.
3. **What's our success rate FOR THIS VERSION?** Compare to previous version to see if recent changes helped.
4. **What tools fail repeatedly?** Fix or replace them.
5. **What tools go unused?** Check traces for tools that were available but never called.
6. **What does the agent say it needs?** Trust and provide.
7. **Is the agent's reasoning sound?** Read traces deeply (via trace-explorer) to find out.
8. **Is the prompt accumulating patches?** Count conditional exceptions added in recent sessions. If >3 patches since last rewrite, evaluate a structural rewrite (Phase 4, Priority 0).
9. **What would make this process better?** Update this document.

## Phase 6: Queue Next Evaluation

**This is the final output of every feedback loop session.** After all analysis and changes are complete, propose the next batch of sessions to run.

### Why This Is Last

Each feedback loop session should:

1. Analyze existing sessions (Phases 1-2)
2. Make improvements based on findings (Phase 4)
3. Queue NEW sessions that will test whether those improvements helped

### Selection Criteria

Choose sessions that:

- Are diverse in task type (cover different capabilities)
- Would test the agent's reasoning on challenging topics
- Exercise recently fixed or newly added tools
- Include edge cases where the agent previously struggled

### Output Format

End your analysis document with the proposed session commands:

```bash
# Evaluation queue from feedback loop YYYY-MM-DD
# Rationale: [brief explanation of what these test]
uv run python -m lup.environment.cli loop "task1" "task2" "task3"
```

### Feedback Cycle

The user runs the sessions, then the next feedback loop session:

1. Collects those results in Phase 1
2. Evaluates quality against the improvements made
3. Queues more sessions → repeat
