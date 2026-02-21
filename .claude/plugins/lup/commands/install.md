---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Install lup plugin and scaffolding into a target repo
argument-hint: [target-repo] [--interactive]
---

# Install Lup into Target Repo

Install the lup plugin, hooks, and useful scaffolding into an existing repository. Unlike `/lup:init` (which customizes the template for a new domain), this command ports lup capabilities into a repo that already has its own structure and conventions.

## Your Task

**Arguments provided**: $ARGUMENTS

### Parse Arguments

- **target-repo**: Path to the target repository (default: `..`). Resolve relative paths from the current working directory.
- **--interactive**: If present, use AskUserQuestion to offer choices for each porting decision. If absent, be conservative — modify as few files as possible.

If `$ARGUMENTS` is empty, use defaults: target=`..`, non-interactive.

## Phase 1: Analyze Source Repo (Lup Template)

Inventory what the lup plugin offers. Read these key files in the **current** repo (`.`):

### Plugin Structure

- `.claude/plugins/lup/.claude-plugin/plugin.json` — plugin identity
- `.claude/plugins/lup/hooks/hooks.json` — hook definitions
- `.claude/plugins/lup/hooks/scripts/*.py` — permission hooks (auto_allow_bash, auto_allow_edits, auto_allow_fetch, pre_push_check, check_plan_md, protect_tests)
- `.claude/plugins/lup/commands/*.md` — slash commands
- `.claude/plugins/lup/agents/*.md` — agent definitions
- `.claude/plugins/lup/TEMPLATE_CLAUDE.md` — CLAUDE.md template

### Reusable Library Code

- `src/lup/lib/` — utilities (trace, hooks, metrics, scoring, cache, retry, notes, mcp, responses, history)
- `src/lup/version.py` — version tracking pattern

### DevTools CLI

The `lup-devtools` CLI (`src/lup/devtools/`) gives Claude Code structured commands for development tasks that would otherwise require ad-hoc bash one-liners. Without it, Claude resorts to `python -c "..."` snippets or manual shell pipelines for trace analysis, feedback collection, and session management — which are fragile and unrepeatable. The devtools encode these workflows as proper CLI commands with argument parsing, output formatting, and error handling.

- `src/lup/devtools/main.py` — root typer app composing sub-apps (entry point: `lup-devtools`)
  - `api.py` — API inspection, module info
  - `dev.py` — worktree management
  - `git.py` — session commit operations
  - `sync.py` — upstream sync tracking
  - `usage.py` — Claude Code usage display
  - `feedback.py` — feedback collection
  - `trace.py` — trace analysis
  - `metrics.py` — aggregate metrics

### Configuration Patterns

- `.claude/settings.json` — settings structure
- `downstream.json` — upstream sync tracking

Build a mental inventory of **portable capabilities** organized by category:

1. **Plugin infrastructure**: hooks.json, hook scripts, plugin.json structure
2. **Permission hooks**: auto-allow patterns for Bash, Edit, WebFetch; pre-push quality gates; test protection
3. **Slash commands**: which ones are generic (commit, rebase, close, clean-gone, meta, update-docs, debug, refactor) vs lup-specific (init, feedback-loop, bump, update)
4. **Library utilities**: print_block, TraceLogger, version tracking, retry decorator, cache, hook composition
5. **CLAUDE.md patterns**: coding standards, git workflow, editing style, debugging philosophy
6. **DevTools patterns**: CLI structure, sync tracking

## Phase 2: Analyze Target Repo

Read the target repo to understand its structure:

1. **Top-level layout**: `ls` the root, look for `src/`, `lib/`, `tests/`, `.claude/`, `package.json`, `pyproject.toml`, `Cargo.toml`, etc.
2. **Language and ecosystem**: Python/Node/Rust/Go/etc? Package manager? Build tools?
3. **Existing `.claude/` setup**: Does it have CLAUDE.md? settings.json? Any plugins already?
4. **Existing hooks**: Any PreToolUse hooks? Permission patterns?
5. **Existing commands**: Any slash commands already defined?
6. **Git workflow**: How does the repo handle branches, PRs, commits?
7. **Code conventions**: What patterns does the repo follow? Type checking? Linting?

**Key questions to answer:**

- What language/ecosystem is the target? (This determines which library utilities are portable)
- Does it already have a `.claude/` setup that we'd be extending vs. creating from scratch?
- What existing conventions must be respected?

## Phase 3: Find the Overlap

Based on the analysis, classify each lup capability as:

### Always Portable (language-agnostic)

These work in any repo:

- **Plugin infrastructure**: The `.claude/plugins/lup/` directory structure itself
- **Permission hooks**: auto_allow_bash (adapt patterns), auto_allow_edits (adapt for target's file types), auto_allow_fetch (adapt URL patterns)
- **Pre-push quality gates**: Adapt to target's linter/type-checker/test runner
- **Generic commands**: commit, rebase, close, clean-gone, meta, update-docs, debug, refactor, add-command, modify-command, merge-conflict
- **CLAUDE.md patterns**: Git workflow, editing style, asking questions, debugging philosophy
- **Settings patterns**: permission structure in settings.json

### Portable if Python

These port well to other Python projects:

- **Library utilities**: hook composition, version tracking, retry, cache
- **DevTools CLI**: The `lup-devtools` typer app structure — `main.py` composing sub-apps, `pyproject.toml` entry point. Even if the target doesn't need every subcommand, the skeleton (api, dev, git, sync) gives Claude Code reliable tooling instead of ad-hoc scripts.
- **Upstream sync**: downstream.json + sync commands (`lup-devtools sync`)

### Portable if Agent SDK

If the target repo uses (or will use) the Claude Agent SDK, the **self-improvement loop scaffolding** is the core value of lup — these are high-priority to port:

- **Agent scaffolding**: core.py pattern (orchestration), subagents.py, models.py (structured output), prompts.py, tool_policy.py, config.py (pydantic-settings)
- **Feedback loop**: feedback collection, trace analysis, metrics aggregation, scoring CSV
- **Session management**: CLI with `run` + `loop` commands, auto-commit, session storage
- **DevTools**: The full `lup-devtools` CLI (trace, feedback, metrics, git commit-results)
- **Version tracking**: version.py pattern for tracking agent behavior changes
- **Commands**: `init`, `feedback-loop`, `bump`, `update` — the self-improvement workflow
- **TEMPLATE_CLAUDE.md**: Section-level merge into the target's existing CLAUDE.md (add missing sections, leave existing ones)

When the target has Agent SDK code, adapt the scaffolding to wrap their existing agent — don't replace it. The lup patterns (trace logging, scoring, feedback collection) layer on top of whatever agent they already have.

### Skip (never port)

- Domain-specific tool implementations (example.py contents)
- Domain-specific prompt content
- Domain-specific model fields (but port the pattern/structure)

## Phase 4: Decide Plugin Strategy

Before deciding what to install, determine **where** it goes. Two options:

### Option A: Install lup as its own plugin (preferred)

Create `.claude/plugins/lup/` as a standalone local plugin in the target repo. This requires:

1. **Plugin directory**: `.claude/plugins/lup/.claude-plugin/plugin.json`
2. **Local marketplace** in settings.json — add `extraKnownMarketplaces.local` pointing to the target's `.claude/plugins/` directory:
   ```json
   "extraKnownMarketplaces": {
     "local": { "source": { "source": "directory", "path": "." } }
   }
   ```
3. **Enable the plugin** in settings.json:
   ```json
   "enabledPlugins": { "lup@local": true }
   ```

This is the cleanest approach — lup lives in its own namespace, hooks don't collide, commands get the `lup:` prefix.

### Option B: Merge into an existing plugin

If the target already has a local plugin (e.g., `.claude/plugins/myproject/`), offer to merge lup's hooks and commands into it. This avoids a second plugin but mixes namespaces. Only do this in interactive mode when the user explicitly chooses it.

**In non-interactive mode, always use Option A.**

When the target already has `extraKnownMarketplaces.local` and other local plugins, lup installs alongside them naturally — no conflict.

## Phase 5: Decide What to Install

Use your judgment based on what you found in Phases 1-3. The analysis should drive the decisions — don't follow a fixed checklist.

### Non-Interactive Mode (default)

Be conservative — only install what clearly adds value. Typical candidates (but decide based on the actual target):

- **Plugin infrastructure**: plugin.json, hooks.json, settings.json (local marketplace + plugin enablement)
- **Permission hooks** adapted to the target's ecosystem (its build tool, test runner, linter, doc URLs)
- **Generic commands** that work in any repo (git workflow, CLAUDE.md maintenance, meta, refactor, etc.)
- **CLAUDE.md**: Perform a **section-level merge** using `TEMPLATE_CLAUDE.md` (`.claude/plugins/lup/TEMPLATE_CLAUDE.md`). Read the template, adapt it for the target's project name and ecosystem, then compare sections against the target's existing CLAUDE.md. Add sections that are missing; leave existing sections untouched. If no CLAUDE.md exists, create one from the adapted template.
- **If Agent SDK detected**: Also install the self-improvement scaffolding — this is lup's core value. The feedback loop commands, lib utilities (trace, scoring, metrics, hooks, version), devtools CLI pattern, session/trace directory structure, downstream.json for sync. Adapt to layer on top of the target's existing agent, not replace it.

**Constraints** in non-interactive mode:

- Don't rewrite existing CLAUDE.md content or change existing hooks/commands
- Don't install anything requiring new dependencies (suggest them in the report)
- Don't modify existing source code files (only create new files)

### Interactive Mode

Use AskUserQuestion at decision points where the user's input matters — don't ask about things you can decide confidently from the analysis, and don't enumerate every file individually.

Group decisions at meaningful levels. Examples of the _kinds_ of things to surface:

- Plugin strategy (own plugin vs merge) when the target already has plugins
- Which capability categories to install when the target could use some but not all
- How to handle CLAUDE.md when the target has one with different conventions
- Whether/how to port Agent SDK scaffolding when the target has existing agent code
- Whether to restructure existing code to fit lup patterns or layer on top
- Offering rewrites or retemplating of existing files when they'd benefit from lup patterns

What questions to ask — and how many — depends entirely on what you found. A bare repo with no `.claude/` needs fewer questions than one with an established plugin ecosystem.

## Phase 6: Execute Installation

For each item being installed:

1. **Read the source file** from the current repo
2. **Adapt it** for the target:
   - Replace `uv run` with target's equivalent (npm run, cargo, make, etc.) in hooks and commands
   - Replace `pyright` / `ruff` / `pytest` with target's tools in pre_push_check
   - Adjust file path patterns in hooks for target's directory structure
   - Keep command markdown structure but update tool references and examples
3. **Write to the target repo** — create directories as needed
4. **Never overwrite** existing files without asking (even in non-interactive mode, warn and skip)

### Installation Order

1. `.claude/plugins/lup/.claude-plugin/plugin.json`
2. `.claude/plugins/lup/hooks/hooks.json` (only reference hooks being installed)
3. `.claude/plugins/lup/hooks/scripts/` — adapted hook scripts
4. `.claude/plugins/lup/commands/` — selected commands
5. `src/<project>/devtools/` — devtools CLI skeleton (if Python target, adapt package name and entry point)
6. `.claude/settings.json` — create or merge
7. `.claude/CLAUDE.md` — section-level merge from TEMPLATE_CLAUDE.md (read template → adapt for target → compare sections → add missing ones → leave existing untouched)

## Phase 7: Verify & Report

After installation:

1. **List all files created/modified** in the target repo
2. **Show a summary** of what was installed and why
3. **Note what was skipped** and why (especially in non-interactive mode)
4. **Suggest next steps**:
   - Review the installed hooks and adjust patterns
   - Try `/lup:meta` to review the .claude structure
   - Run `/lup:commit` to test the commit workflow
   - Consider `/lup:update` later for ongoing sync

## Guidelines

- **Respect the target**: Don't impose lup conventions where the target has its own. Adapt to them.
- **Minimal footprint**: In non-interactive mode, prefer doing less. The user can always run with `--interactive` later to add more.
- **No new dependencies**: Don't install anything that requires `pip install` or `npm install` unless explicitly approved in interactive mode.
- **Adapt, don't copy**: Every file needs to be reviewed and adapted for the target's ecosystem.
- **Preserve existing work**: Never overwrite existing `.claude/` files. Merge or extend.
- **Explain decisions**: For each installed item, briefly explain what it does and why it helps.
