---
allowed-tools: Read, Edit, Write, Glob, Grep, AskUserQuestion
description: Modify an existing slash command based on a description or delta
argument-hint: [command-name] [delta or description] [--args hint1 hint2]
---

# Modify Existing Slash Command

## Your Task

The user wants to MODIFY an existing slash command. Parse the arguments to determine which command to change and how.

**Arguments provided**: $ARGUMENTS

### How to Parse Arguments

The first word is the **command name** to modify. Everything after is the **delta** (what to change) or a **new description** (replace the command's behavior entirely), with an optional `--args` flag.

**Basic:** `/lup:modify-command commit Add a step that runs ruff format before committing`

- Command name: `commit`
- Delta: "Add a step that runs ruff format before committing"

**With args:** `/lup:modify-command debug Add verbose flag --args [error] [--verbose]`

- Command name: `debug`
- Delta: "Add verbose flag"
- New argument hints: `[error] [--verbose]`

When `--args` is provided, update the command's `argument-hint` frontmatter to the specified hints and ensure `$ARGUMENTS` is handled in the command body.

### If No Arguments Provided

If `$ARGUMENTS` is empty, ask the user:

- Which command should be modified?
- What changes should be made?

### Steps

1. **Parse** the command name and delta from the arguments
2. **Find** the command file -- search in these locations:
   - `.claude/plugins/lup/commands/<name>.md` (plugin commands)
   - `.claude/commands/<name>.md` (project commands)
   - `~/.claude/commands/<name>.md` (personal commands)
   - Also check for namespaced variants (e.g., `lup:name` -> `.claude/plugins/lup/commands/name.md`)
3. **Read** the current command file in full
4. **Analyze** the delta -- determine whether the user wants to:
   - **Add** new behavior (append steps, add sections)
   - **Change** existing behavior (modify instructions, update tools)
   - **Remove** behavior (simplify, strip sections)
   - **Replace** entirely (new description overrides old)
5. **Show the user** the proposed changes using AskUserQuestion:
   - Summarize what will change
   - Show before/after for key sections if helpful
   - Ask for confirmation before writing
6. **Apply** the changes -- edit or rewrite the command file
7. **Update frontmatter** if needed (e.g., new `allowed-tools` for added functionality)
8. **Confirm** the modification and show a summary

### Guidelines

- **Preserve the command's structure and style** -- match the formatting patterns of the existing command
- **Don't over-modify** -- only change what the delta requires. If the user says "add X", don't also reorganize unrelated sections.
- **Update allowed-tools** if the delta introduces new tool requirements (e.g., adding a git step requires `Bash(git:*)`)
- **Keep the command self-contained** -- it should work without requiring the user to remember the delta
- **Preserve working behavior** -- don't break existing functionality unless the user explicitly asks to replace it
