---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Create a new slash command in the lup plugin
argument-hint: [name] [description]
---

# Add New Command

Create a new slash command in `.claude/plugins/lup/commands/`.

## Your Task

Help the user create a new slash command. Commands are markdown files with YAML frontmatter.

**Arguments provided**: $ARGUMENTS

### How to Parse Arguments

The first word is the **command name**. Everything after is the **description** (what the command does).

**Examples:**

- `/lup:add-command review` — name is `review`, description not provided (ask)
- `/lup:add-command review Analyze PR diffs and suggest improvements` — name is `review`, description is "Analyze PR diffs and suggest improvements"

### If No Arguments Provided

If `$ARGUMENTS` is empty, proceed to Phase 1 and ask for everything.

## Phase 1: Gather Requirements

Use AskUserQuestion to gather any info **not already provided via arguments**. Skip questions that were answered inline.

1. **Command name**: What should the command be called? (e.g., `review`, `test`, `deploy`)
2. **Purpose**: What does this command do?
3. **Arguments**: Does this command accept arguments? If yes, define an `argument-hint` (e.g., `[target]`, `[file] [--verbose]`, `<required-arg>`). Arguments are passed to the command via `$ARGUMENTS`.
4. **Tools needed**: Which tools should be allowed? Common options:
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
argument-hint: <hint from phase 1, omit if no arguments>
---

# <Command Title>

<Brief description of what this command does>

## Your Task

**Arguments provided**: $ARGUMENTS

<Instructions for Claude when this command is invoked>
<If the command accepts arguments, include parsing logic for $ARGUMENTS>

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

### Command with arguments:

```markdown
---
allowed-tools: Bash, Read, Glob, Grep
description: Run tests for a specific module
argument-hint: [module-name] [--verbose]
---

# Run Module Tests

Run tests for a specific module.

## Your Task

**Arguments provided**: $ARGUMENTS

Parse the arguments: first word is the module name, `--verbose` flag enables detailed output.
If no module name provided, ask the user which module to test.

1. Find test files for the module
2. Run the tests
3. Report results
```

## Notes

- Command names should be lowercase with hyphens (e.g., `my-command`)
- Keep descriptions under 80 characters
- Include clear steps in the command body
- Use AskUserQuestion for interactive commands
- Add `argument-hint` frontmatter when the command accepts arguments — use `[optional]` brackets and `<required>` angles
- Reference `$ARGUMENTS` in the command body to receive the user's input
- Always include a fallback (e.g., AskUserQuestion) when arguments are empty
