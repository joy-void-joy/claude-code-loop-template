---
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, Task, AskUserQuestion
description: Review and modify .claude structure, brainstorm improvements interactively
---

# Meta: .claude Structure Review & Improvement

You are reviewing the `.claude/` directory structure and brainstorming improvements with the user.

## User's Direction

$ARGUMENTS

## Your Task

Based on the user's input above, explore the relevant parts of `.claude/` and brainstorm solutions. The `.claude/` directory contains:

- `CLAUDE.md` - Project instructions and documentation
- `settings.json` - Permissions and plugin configuration
- `plugins/lup/` - Self-improvement loop plugin with commands, hooks, and agents

Read the relevant files based on what the user is asking about, then use AskUserQuestion to propose specific changes or additions.

## Plugin Structure Reference

```
plugins/lup/
├── .claude-plugin/plugin.json   # Plugin metadata
├── commands/                    # Slash commands
│   ├── brainstorm.md            # Pre-init design exploration
│   ├── init.md                  # Domain initialization wizard
│   ├── feedback-loop.md         # 3-level meta analysis
│   └── meta.md                  # This file
├── hooks/                       # PreToolUse permission hooks
│   ├── hooks.json               # Hook definitions
│   └── scripts/                 # Hook implementations
│       ├── auto_allow_bash.py   # Bash command auto-allow/deny
│       ├── auto_allow_edits.py  # Edit auto-allow (trivial changes)
│       ├── auto_allow_fetch.py  # WebFetch URL allow/deny
│       ├── pre_push_check.py    # Quality gates before push
│       ├── check_plan_md.py     # PLAN.md check on feature branches
│       └── protect_tests.py     # TDD test protection
├── agents/                      # Subagent definitions
└── TEMPLATE_CLAUDE.md           # CLAUDE.md template for new projects
```

**Note:** Python CLI tooling (API inspection, trace analysis, feedback collection, worktree management, etc.) lives in `src/lup/devtools/` and is exposed as the `lup-devtools` CLI entry point. See the lup-devtools section in CLAUDE.md.

### When to Add to the Plugin

- **Commands**: Reusable workflows invoked via `/lup:command-name`
- **Hooks**: Permission hooks in `hooks/scripts/` — auto-allow, deny, or quality gates
- **Agents**: Subagent definitions for specialized tasks
- **Devtools**: Python CLI tools go in `src/lup/devtools/` (exposed as `lup-devtools`), not in the plugin

## Brainstorming Principles

- **Propose, don't assume**: Always use AskUserQuestion before making changes
- **Show context**: When proposing changes, show the relevant current state first
- **Group related changes**: Batch related improvements into single proposals
- **Explain rationale**: Every suggestion should include why it would help
- **Offer alternatives**: When there are multiple valid approaches, present options

## First Principles Design

When considering changes, ask:

1. **Bitter Lesson Check**: Does this add a capability, or just a rule?
   - Prefer tools and capabilities over prompt constraints
   - Avoid pattern-matching patches

2. **Generality Check**: Would this help if the domain changed?
   - General principles > specific patches
   - If it only works for one scenario, it's probably over-fitted

3. **Meta Level Check**: Are we changing the right layer?
   - Object level = the agent's behavior
   - Meta level = how the agent tracks itself
   - Meta-meta level = the feedback loop infrastructure

## Command Evolution

**After every command invocation**, reflect on how it was actually used:

1. **Compare intent vs usage**: Did the user use the command as documented, or did they adapt it?
2. **Notice patterns**: If the user provides documentation, links, or redirects the command's focus, that's a signal the command should evolve.
3. **Proactively propose updates**: When you notice the command being used differently than documented:
   - Use AskUserQuestion to propose updating the command
   - Include the specific usage pattern you observed
   - Suggest concrete changes to the command file

## Process

1. Read relevant files based on the user's direction
2. Analyze and identify potential improvements
3. Use AskUserQuestion to propose specific changes with rationale
4. Implement approved changes immediately
5. **Reflect on this command's execution** and propose updates to meta.md if warranted
6. Continue brainstorming or summarize changes made
