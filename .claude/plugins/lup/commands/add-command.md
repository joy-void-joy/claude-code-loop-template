---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Create a new slash command in the lup plugin
---

# Add New Command

Create a new slash command in `.claude/plugins/lup/commands/`.

## Your Task

Help the user create a new slash command. Commands are markdown files with YAML frontmatter.

## Phase 1: Gather Requirements

Use AskUserQuestion to understand:

1. **Command name**: What should the command be called? (e.g., `review`, `test`, `deploy`)
2. **Purpose**: What does this command do?
3. **Tools needed**: Which tools should be allowed? Common options:
   - `Read, Glob, Grep` - For read-only exploration
   - `Read, Write, Edit, Glob, Grep` - For file modifications
   - `Bash, Read, Write, Edit, Glob, Grep` - For running commands + file ops
   - `AskUserQuestion` - For interactive commands

## Phase 2: Create the Command

Create the file at `.claude/plugins/lup/commands/<name>.md`:

```markdown
---
allowed-tools: <tools from phase 1>
description: <one-line description>
---

# <Command Title>

<Brief description of what this command does>

## Your Task

<Instructions for Claude when this command is invoked>

## Steps

1. <Step 1>
2. <Step 2>
3. ...

## Output

<What the command should produce>
```

## Phase 3: Verify

After creating the command:

1. Show the user the file contents
2. Explain how to invoke it: `/lup:<command-name>`
3. Ask if any adjustments are needed

## Template Examples

### Read-only analysis command:

```markdown
---
allowed-tools: Read, Glob, Grep
description: Analyze code structure and patterns
---

# Analyze Codebase

Analyze the codebase structure and report findings.

## Your Task

1. Use Glob to find relevant files
2. Use Grep to search for patterns
3. Use Read to examine key files
4. Report findings in a structured format
```

### Interactive workflow command:

```markdown
---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Interactive code review workflow
---

# Code Review

Guide the user through a code review.

## Your Task

1. Ask what to review
2. Read the relevant files
3. Provide feedback
4. Offer to make changes
```

## Notes

- Command names should be lowercase with hyphens (e.g., `my-command`)
- Keep descriptions under 80 characters
- Include clear steps in the command body
- Use AskUserQuestion for interactive commands
