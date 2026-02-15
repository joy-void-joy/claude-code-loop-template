---
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
description: Rewrite a file or folder from scratch while respecting coding conventions
argument-hint: <path>
---

# Refactor from Scratch

Rewrite a file (or folder) from scratch, preserving intent but enforcing coding conventions.

## Your Task

**Arguments provided**: $ARGUMENTS

### Parse Arguments

The argument is a **file or folder path**. If no path is provided, use AskUserQuestion to ask which file or folder to refactor.

Resolve relative paths against the current working directory.

## Steps

### 1. Validate the target

- Confirm the path exists (file or directory)
- If it's a directory, list all files that will be refactored using Glob
- Show the user what will be refactored and ask for confirmation

### 2. Create a backup

Copy the target to `<path>.bak` (file) or `<path>.bak/` (directory):

```
cp -r <path> <path>.bak
```

Confirm the backup was created successfully before proceeding.

### 3. Understand the original

For each file being refactored:

- Read the entire file
- Identify its **purpose**: what does this code do?
- Identify its **public interface**: exports, function signatures, class APIs
- Identify its **dependencies**: imports, external calls
- Identify its **side effects**: file I/O, network calls, state mutations
- Note any tests that import from or test this file (use Grep to find references)

### 4. Read coding conventions

Read the project's CLAUDE.md (`.claude/CLAUDE.md`) to understand:

- Type safety requirements
- Error handling philosophy
- Code style preferences
- Library choices and patterns
- DRY principles and where utilities belong

Also scan neighboring files in the same package to understand local patterns and conventions.

### 5. Rewrite from scratch

For each file, **write it fresh** using the Write tool — do not edit the original incrementally. The rewrite must:

- **Preserve the full public interface** (same exports, same function signatures, same behavior)
- **Include everything the original included** — no features dropped, no edge cases lost
- **Follow all coding conventions** from CLAUDE.md (types, error handling, style, etc.)
- **Improve structure** where the original was unclear or poorly organized
- **Keep the same filename and location**

### 6. Verify

After rewriting:

- Run `uv run pyright` to check for type errors in the rewritten files
- Run `uv run ruff check` to verify lint compliance
- If tests exist for the refactored code, run them with `uv run pytest <test_file>`
- Report any issues found and fix them

### 7. Summary

Show the user:

- What was refactored
- Where the backup lives (`<path>.bak`)
- Key improvements made
- Any issues found during verification
- Remind them: `rm <path>.bak` when satisfied

## Important

- **Never drop functionality.** The rewrite must do everything the original did.
- **Ask before proceeding** if the target is large (>5 files or >500 lines total).
- **Preserve tests.** If tests reference the refactored code, ensure they still pass.
- If the backup path already exists, ask the user before overwriting it.
