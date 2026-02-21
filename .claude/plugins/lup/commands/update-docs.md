---
allowed-tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Update CLAUDE.md with learnings from this session
---

# Update Documentation

Update CLAUDE.md and other documentation based on learnings from this session.

## Your Task

Review the current session and update documentation to reflect:

- New patterns discovered
- Corrections to existing guidance
- New commands or workflows
- Architectural decisions

## Phase 1: Review Current State

1. Read the current `.claude/CLAUDE.md`
2. Review what happened in this session:
   - What problems were solved?
   - What patterns worked well?
   - What corrections were needed?
   - What new knowledge was gained?

## Phase 2: Identify Updates

Look for opportunities to update:

### CLAUDE.md sections:

- **Project Overview**: Has the scope changed?
- **Reference Files**: Are there new important files?
- **Commands**: Any new commands to document?
- **Code Style**: New patterns or conventions?
- **Anti-patterns**: Mistakes to avoid in the future?

### Other docs:

- **README.md**: User-facing changes?
- **Command files**: Need updates to existing commands?

## Phase 3: Propose Changes

Use AskUserQuestion to propose specific updates:

1. Show the current text
2. Show the proposed change
3. Explain why this update would help
4. Ask for approval before making changes

## Phase 4: Apply Updates

For each approved change:

1. Use Edit to make the change
2. Show the result
3. Confirm with the user

## Guidelines

- **Be concise**: Documentation should be scannable
- **Be specific**: Avoid vague guidance
- **Be current**: Remove outdated information
- **No history**: Don't add comments like "updated on X date"

## Example Updates

### Good update:

```markdown
# Before

Use `uv run forecast test` to run tests.

# After

Use `uv run pytest` to run tests. Use `-k pattern` to filter.
```

### Bad update (don't do this):

```markdown
# Don't add temporal markers

Use `uv run pytest` to run tests. (Updated Feb 2026 to fix command)
```

The git history captures when changes were made. Documentation should read as if it was always correct.
