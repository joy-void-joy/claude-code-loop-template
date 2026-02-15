---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Task
description: Propagate a general principle across the entire repo
argument-hint: <principle description>
---

# Propagate Principle

Take a general principle and ensure the entire repo reflects it — documentation, commands, hook scripts, code templates, agent prompts, and library patterns.

The principle should be visible at every layer: the docs that describe how to work, the commands that encode workflows, the hooks that enforce rules, and the code that serves as the starting template for new projects.

## User's Principle

$ARGUMENTS

## Your Task

Propagate the principle above across all layers of the repository. Work through the phases below, proposing changes in grouped batches for user approval.

## Phase 1: Formulate the Principle

Before auditing files, articulate the principle precisely:

1. **State the principle** in one clear sentence
2. **Identify the "do this / not this" pair** — what does the principle look like when followed vs violated?
3. **Check generality** — would this principle still apply if the domain changed completely? If not, it may be too specific.

Use AskUserQuestion to confirm the formulation with the user before proceeding. Show:
- The principle statement
- A "Do This / Not This" table (like the Bitter Lesson table in CLAUDE.md)
- 2-3 concrete examples of the principle in action

## Phase 2: Audit All Layers

Read every relevant file and categorize findings into three buckets:

- **Already reflected** — the principle is present and correctly applied
- **Missing** — a place where the principle should be reflected but isn't
- **Contradicted** — a place that actively violates the principle

### Layer A: Documentation & Meta

1. **CLAUDE.md** (`.claude/CLAUDE.md`)
   - Check every section: does it align with or contradict the principle?
   - Look for existing principles that overlap or conflict

2. **TEMPLATE_CLAUDE.md** (`.claude/plugins/lup/TEMPLATE_CLAUDE.md`)
   - Same checks — this is what new projects inherit

### Layer B: Commands & Workflows

3. **All command files** (`.claude/plugins/lup/commands/*.md`)
   - Read each command's instructions, guidelines, and anti-patterns
   - Check if commands encode workflows that violate the principle

### Layer C: Hook Scripts & Enforcement

4. **Hook scripts** (`.claude/plugins/lup/hooks/scripts/*.py`)
   - Check if any hook logic contradicts the principle
   - Consider if a new hook could enforce the principle mechanically

### Layer D: Code Template

The `src/` directory IS the template — when someone forks this repo, this code is their starting point. The principle should be visible in how the template code is written.

5. **Agent code** (`src/lup/agent/`)
   - `core.py` — orchestration patterns, how the agent is structured
   - `prompts.py` — system prompts, instructions to the SDK agent
   - `subagents.py` — how subagents are defined and used
   - `tool_policy.py` — how tools are made available
   - `tools/*.py` — example tool implementations
   - `models.py`, `config.py` — data modeling patterns

6. **Library code** (`src/lup/lib/`)
   - Reusable abstractions — do they embody or contradict the principle?
   - Patterns that downstream users will copy

7. **Environment code** (`src/lup/environment/`)
   - CLI structure, how the agent is invoked
   - Any scaffolding patterns

8. **Devtools** (`src/lup/devtools/`)
   - CLI commands for development and analysis
   - Patterns encoded in automation

## Phase 3: Propose Changes (Grouped by Layer)

Present findings and proposed changes one layer at a time. For each layer:

1. **Show current state** — quote the relevant sections that need changes
2. **Propose specific edits** — show what would change and why
3. **Use AskUserQuestion** to get approval before proceeding

### Layer order:

**Group 1: CLAUDE.md + TEMPLATE_CLAUDE.md**
- CLAUDE.md is the source of truth. Changes here set the direction for everything else.
- Consider: new section, additions to existing sections, anti-pattern entries, removal of contradictions.
- Mirror relevant changes into TEMPLATE_CLAUDE.md so new projects inherit the principle.
- Keep template sections general — domain-specific details belong in CLAUDE.md only.

**Group 2: Command files**
- Update commands whose workflows should reflect the principle.
- Add the principle to relevant "Guidelines" or "Anti-Patterns" sections.
- Don't add the principle to every command — only where it's relevant to that command's workflow.

**Group 3: Code template (src/)**
- This is where the principle becomes tangible. The code IS the example.
- Agent orchestration (`core.py`, `subagents.py`) — does the structure reflect the principle?
- Prompts (`prompts.py`) — does the SDK agent's system prompt embody the principle?
- Tools (`tools/*.py`, `tool_policy.py`) — do the example tools demonstrate the principle?
- Library (`lib/`) — do shared abstractions follow the principle?
- Consider: refactoring patterns, adding/removing code, changing defaults, updating examples.

**Group 4: Hook scripts & enforcement**
- If the principle can be mechanically enforced, propose a hook.
- If an existing hook contradicts the principle, propose modifications.
- Not every principle needs a hook — only propose one if mechanical enforcement makes sense.

**Group 5: Scripts & automation**
- Do the feedback loop scripts, commit scripts, or other automation reflect the principle?
- Are there scripts that should exist to support the principle but don't?

## Phase 4: Execute Approved Changes

For each approved group, make the edits. After all changes:

1. Summarize what was changed across all layers
2. Note any layers where no changes were needed (and why)
3. Flag any areas where the principle COULD apply but you chose not to change (with rationale)

## Principles for Principle Propagation

- **Consistency over completeness** — better to have 5 files consistently reflecting the principle than 10 files with half-baked mentions
- **Don't dilute existing content** — integrate naturally into existing sections rather than bolting on disconnected paragraphs
- **Respect the structure** — each file type has conventions. CLAUDE.md uses tables and sections, commands use phases, hooks use pattern lists
- **Less is more** — a principle mentioned in 3 right places is better than mentioned in 15 places where it becomes noise
- **Enforcement > documentation** — a hook that prevents violations is worth more than a paragraph that describes the principle
