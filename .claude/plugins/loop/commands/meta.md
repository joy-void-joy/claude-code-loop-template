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
- `plugins/loop/` - Self-improvement loop plugin with commands, scripts, and agents

Read the relevant files based on what the user is asking about, then use AskUserQuestion to propose specific changes or additions.

## Plugin Structure Reference

```
plugins/loop/
├── .claude-plugin/plugin.json   # Plugin metadata
├── commands/                    # Slash commands
│   ├── init.md                  # Domain initialization wizard
│   ├── feedback-loop.md         # 3-level meta analysis
│   └── meta.md                  # This file
├── scripts/                     # Python CLI tools
│   ├── feedback_collect.py      # Session feedback collection
│   ├── trace_analysis.py        # Reasoning trace inspection
│   └── aggregate_metrics.py     # Cross-session metrics
└── agents/                      # Subagent definitions (if needed)
```

### When to Add to the Plugin

- **Commands**: Reusable workflows invoked via `/loop:command-name`
- **Scripts**: Python CLI tools run via `uv run python .claude/plugins/loop/scripts/X.py`
- **Agents**: Subagent definitions for specialized tasks

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
