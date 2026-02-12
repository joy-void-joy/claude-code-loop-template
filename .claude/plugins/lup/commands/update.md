---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, AskUserQuestion
description: Review upstream template commits and apply improvements
---

# Update from Upstream

Review commits from tracked upstream repositories (by default, the lup template repo) since the last sync. Classify each commit as portable or domain-specific, then apply selected improvements to the current project.

## Setup

If `downstream.json` does not exist, help the user set it up:

```bash
# Set a local path for the lup template repo
uv run python .claude/plugins/lup/scripts/claude/downstream_sync.py setup lup /path/to/lup-template.git/tree/main

# Or mark it as already synced at current HEAD (skip old history)
uv run python .claude/plugins/lup/scripts/claude/downstream_sync.py setup lup /path/to/lup-template.git/tree/main --synced
```

Ask the user for the path to their lup template repo if not already tracked.

## Process

### 1. Check for new commits

```bash
uv run python .claude/plugins/lup/scripts/claude/downstream_sync.py list
```

If no projects have new commits, report that everything is up to date and stop.

### 2. Review commit history

For each project with new commits:

```bash
uv run python .claude/plugins/lup/scripts/claude/downstream_sync.py log <project>
```

Read through the commit history. The commit messages preserve intent — a message like "feat(lib): add TTL cache invalidation" tells you exactly what changed and why.

### 3. Classify each commit

For each commit, read the full diff:

```bash
uv run python .claude/plugins/lup/scripts/claude/downstream_sync.py diff <project> <sha>
```

Classify as:

- **Portable**: General improvements that work for any project built on this template
  - `lib/` utilities (e.g., better `print_block`, new retry patterns, caching improvements)
  - Hook logic improvements (new permission patterns, better auto-allow rules)
  - Script enhancements (better CLI, new analysis tools)
  - Command updates (improved workflows, new phases)
  - Build/config improvements that generalize

- **Domain-specific**: Tied to the upstream project's domain
  - Domain models, API integrations, domain-specific tools
  - Project-specific prompts or agent configurations
  - Data processing unique to that domain

- **Infrastructure**: Build/CI/config changes
  - May or may not apply — evaluate case by case

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

After review is complete (whether or not changes were applied):

```bash
uv run python .claude/plugins/lup/scripts/claude/downstream_sync.py mark-synced <project>
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
- **Ask, don't skip** — when uncertain about a change, present it to the user with your reasoning and let them decide
- **Adapt, don't copy** — upstream code may use different naming, patterns, or structure. Translate to fit the current project.
- **Test after applying** — always run pyright/ruff/pytest after applying changes
- **Mark synced even if nothing applied** — this advances the sync pointer so you don't re-review the same commits next time
