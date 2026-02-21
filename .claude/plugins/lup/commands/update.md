---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, AskUserQuestion
description: Review upstream template commits and apply improvements
argument-hint: [focus area]
---

# Update from Upstream

Review commits from tracked downstream repositories since the last sync. Generalize domain-specific patterns back into the template as domain-neutral scaffolding, then apply selected improvements.

**This repo is both a template and a scaffold.** Downstream repos customize the template (prompts, tools, models) but inherit the scaffold (agents, commands, hooks, workflows). When reviewing downstream changes, ask: "Did this pattern emerge from real use?" If yes, it probably belongs in the template — generalized, with domain-specific details removed.

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

- **Portable as-is**: Improvements that apply directly without modification
  - `lib/` utilities (e.g., better `print_block`, new retry patterns, caching improvements)
  - `devtools/` CLI improvements (new subcommands, better output formatting, new analysis tools)
  - Hook logic improvements (new permission patterns, better auto-allow rules)
  - Build/config improvements that generalize
  - **CLAUDE.md improvements** (coding standards, workflow tips, new guidelines)

- **Portable as scaffold**: Domain-specific implementations that represent a generalizable _pattern_. These get ported with domain details replaced by template placeholders.
  - **New agents/subagents** — A "version-reviewer" that uses Brier scores becomes a scaffold version-reviewer that uses generic outcome metrics. A "forecast reviewer" sub-agent becomes a generic "reviewer" scaffold that critiques agent output.
  - **New tools or tool patterns** — A domain-specific reflection tool becomes a scaffold for structured self-assessment tools. A tool that calls a sub-agent internally is a reusable pattern.
  - **New commands** — A "leak-investigator" for retrodiction becomes a scaffold for investigator-style commands
  - **Workflow improvements** — Offline mode for a specific API becomes a general "graceful degradation" pattern
  - **Reusable lib patterns** — A "response collector" that prints+logs SDK blocks is a general utility. A JSON pretty-printer for tool results belongs in lib.
  - **Feedback loop updates** — Version-scoped analysis, new analysis phases, better templates
  - **Agent SDK usage patterns** (hooks, session config, structured output, tool patterns)
  - **Agent core improvements** that generalize (error handling, log management, config patterns)
  - **Scoring/metrics improvements** (new columns, aggregation methods)

- **Data-only or purely domain-specific**: Skip these
  - Raw data commits (`data(outputs):`, `data(scores):`)
  - API client code for a specific external service with no generalizable pattern
  - Domain-specific prompts that encode knowledge irreducible to a template

**The bias should be strongly toward inclusion.** Most code changes contain generalizable patterns even when they look domain-specific at first. A "Google Trends tool" commit is domain-specific, but if it introduces a new tool design pattern or a new way of structuring MCP responses, that pattern belongs in the template.

**The key question is not "Is this portable?" but "What pattern does this represent?"** A downstream repo adds a version reviewer with Brier scores — the pattern is "structured agent version assessment." That pattern belongs in the template.

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
- **Generalize, don't dismiss** — when a downstream repo adds something domain-specific, ask "what pattern does this represent?" and port the pattern as scaffold. A forecasting-specific agent becomes a domain-neutral agent scaffold.
- **Ask, don't skip** — when uncertain about a change, present it to the user with your reasoning and let them decide
- **Adapt, don't copy** — downstream code uses domain-specific naming, paths, and models. Replace these with template-appropriate equivalents (`lup` package paths, generic metrics, placeholder descriptions).
- **Re-evaluate file placement** — after generalizing, re-check: can this module be used as-is without templating or source modification? If yes, it belongs in `lib/`, not `agent/`. A quick proxy: does it import from `agent/`? Downstream repos may have had domain-specific reasons for a different placement.
- **Test after applying** — always run pyright/ruff/pytest after applying changes
- **Mark synced even if nothing applied** — this advances the sync pointer so you don't re-review the same commits next time
