---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, AskUserQuestion
description: Review upstream template commits and apply improvements
argument-hint: [focus area]
---

# Update from Upstream

Review commits from tracked upstream repositories (by default, the lup template repo) since the last sync. Classify each commit as portable or domain-specific, then apply selected improvements to the current project.

**Optional focus argument:** When a focus area is provided (e.g., `/lup:update hooks`, `/lup:update lib/cache`), only review and port commits that touch the specified area. **Do not mark as synced** — the sync pointer stays unchanged so a future `/lup:update` (without args) still reviews all commits from the same checkpoint.

## Setup

If `downstream.json` does not exist, help the user set it up.

**Self-referencing repos:** When the current repo IS the upstream (e.g., the lup template itself), set `"ignore": true` in `downstream.json.local` to skip it during updates. The committed `downstream.json` still ships the URL so downstream users can sync from it.

```bash
# Set a local path for the lup template repo
uv run lup-devtools sync setup lup /path/to/lup-template.git/tree/main

# Or mark it as already synced at current HEAD (skip old history)
uv run lup-devtools sync setup lup /path/to/lup-template.git/tree/main --synced
```

Ask the user for the path to their lup template repo if not already tracked.

## Process

### 1. Check for new commits

```bash
uv run lup-devtools sync list
```

If no projects have new commits, report that everything is up to date and stop.

### 2. Review commit history

For each project with new commits:

```bash
uv run lup-devtools sync log <project>
```

Read through the commit history. The commit messages preserve intent — a message like "feat(lib): add TTL cache invalidation" tells you exactly what changed and why.

### 3. Classify each commit

**If a focus area was provided:** Skip commits whose diffs don't touch files or concepts related to the focus area. Only review commits where the diff includes changes relevant to the focus (e.g., `/lup:update hooks` → only commits touching hook scripts, hook logic, or hook-related config).

For each commit, read the full diff:

```bash
uv run lup-devtools sync diff <project> <sha>
```

**IMPORTANT: Do not dismiss code changes prematurely.** A commit that touches domain-specific files may still contain portable patterns, SDK usage improvements, or generalizable techniques. Always read the actual diff before classifying.

Classify as:

- **Portable**: General improvements that work for any project built on this template
  - `lib/` utilities (e.g., better `print_block`, new retry patterns, caching improvements)
  - Hook logic improvements (new permission patterns, better auto-allow rules)
  - Script enhancements (better CLI, new analysis tools)
  - Command updates (improved workflows, new phases)
  - Build/config improvements that generalize
  - **Agent SDK usage patterns** (hooks, session config, structured output, tool patterns)
  - **Agent core improvements** that generalize (error handling, log management, config patterns)
  - **Scoring/metrics improvements** that apply to any domain (new columns, aggregation methods)
  - **Feedback loop improvements** (collection, analysis, filtering)
  - **CLAUDE.md improvements** (coding standards, workflow tips, new guidelines)

- **Domain-specific**: Tied to the upstream project's domain
  - Domain models with no generalizable structure
  - API integrations specific to a single external service
  - Domain-specific prompts that can't be abstracted
  - Data processing unique to that domain

- **Mixed**: Contains both portable and domain-specific parts
  - Extract the portable patterns and present them separately
  - Example: A commit adding a Metaculus API client is domain-specific, but its retry/rate-limiting pattern is portable

**The bias should be toward inclusion, not exclusion.** When a commit touches `agent/core.py`, `lib/`, `scoring.py`, or similar shared files, assume it's worth reviewing even if the commit message sounds domain-specific. Read the diff and ask yourself: "Could I generalize this to the template?"

When reviewing diffs, also read the full changed files in both repos for context. File-level diffs help you understand how a change fits into the broader codebase structure.

### 4. Present improvements

For each portable improvement, use AskUserQuestion to present:

- The upstream commit message (intent)
- The relevant diff (what changed)
- Where it maps to in the current project
- Whether to apply it

Group related commits when they form a logical unit of work.

**When uncertain whether a change is portable or domain-specific, ask the user** — don't skip it. Present the commit with your classification reasoning and let the user decide.

### 5. Apply selected changes

For approved improvements:

1. Read the full changed files in both repos to understand context
2. Apply the changes, adapting as needed:
   - Rename domain-specific identifiers to match the current project
   - Adjust import paths (the upstream might use a different package name)
   - Keep the current project's coding conventions
3. Run verification after applying:
   ```bash
   uv run pyright
   uv run ruff check .
   uv run pytest
   ```

### 6. Mark as synced

**Skip this step if a focus area was provided** — the sync pointer must stay unchanged so unreviewed commits are still visible in the next full `/lup:update`.

After a full review is complete (whether or not changes were applied):

```bash
uv run lup-devtools sync mark-synced <project>
```

### 7. Optionally commit

If changes were applied, offer to commit them:

```bash
git add <changed-files>
git commit -m "feat(lib): apply improvements from <project>"
```

## Guidelines

- **Commit-level review preserves intent** — review commits, not flat diffs, so you understand why each change was made
- **File diffs provide context** — use full file diffs alongside commit diffs to understand how changes fit into the codebase
- **Bias toward inclusion** — read every non-data commit's diff before dismissing it. Code changes often contain generalizable patterns even when the commit message sounds domain-specific.
- **Ask, don't skip** — when uncertain about a change, present it to the user with your reasoning and let them decide
- **Adapt, don't copy** — upstream code may use different naming, patterns, or structure. Translate to fit the current project.
- **Test after applying** — always run pyright/ruff/pytest after applying changes
- **Mark synced even if nothing applied** — this advances the sync pointer so you don't re-review the same commits next time
