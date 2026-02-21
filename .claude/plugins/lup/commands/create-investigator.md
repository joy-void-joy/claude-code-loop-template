---
allowed-tools: Write, Read, Glob, Grep, AskUserQuestion
description: Create a new diagnostic/investigator command (like /debug)
argument-hint: [command-name] [brief description of what it investigates]
---

# Create Investigator Command

You are creating a new **investigator command** — a command where the user pastes raw output (logs, errors, console snippets, tool results) with minimal commentary, and the command guides you to trace the issue through code and logs and produce a diagnostic report.

This is distinct from `/lup:add-command` which creates general-purpose commands. Investigator commands share a specific pattern: raw input in, traced diagnosis out.

**Arguments provided**: $ARGUMENTS

## Step 0: Parse arguments

The first word is the **command name**. Everything after is a **brief description** of what the command investigates.

If `$ARGUMENTS` is empty, ask the user what the command should be called and what it investigates.

## Step 1: Understand the domain

Before writing anything, understand what this investigator needs to do:

1. **Read existing investigator commands** as reference:
   - `.claude/plugins/lup/commands/debug.md` — traces errors through logs

2. **Explore the codebase** to understand the domain. Based on the description, identify:
   - What kind of input will users typically paste? (tracebacks, agent reasoning, API responses, metrics, etc.)
   - Where are the relevant logs and artifacts? (`logs/`, `notes/`, other directories)
   - What source code is most relevant? Which files in `src/` would the investigator need to read?
   - What devtools commands might be useful? (`uv run lup-devtools --help`)

3. **Use AskUserQuestion** to align on the design:
   - What are the common scenarios this investigator will handle?
   - What are the typical "anchors" in the pasted output that help trace the issue? (IDs, timestamps, function names, error codes, etc.)
   - What domain-specific knowledge should the command encode? (common failure modes, known gotchas, relevant architecture)

## Step 2: Design the command

Based on your exploration and the user's input, design the command. Existing investigator commands share these traits (but adapt to the domain):

**Philosophy**: "Don't hypothesize — trace." The command should guide you to find actual evidence, not speculate.

**Input handling**: The input is raw pasted output. It may not contain metadata, IDs, or context. The command should explain how to work with incomplete input and what to extract from it.

**Investigation steps**: Domain-specific steps that trace from the pasted input to root cause. Each step should explain:

- What to look for
- Where to look (specific directories, files, scripts)
- What tools/commands to use
- When to ask the user for more context

**Report format**: What happened, why, and how to fix it — adapted to the domain.

**Rules**: Domain-specific rules about what to never do (guess, speculate, etc.) and what to always do (quote evidence, read source, etc.).

## Step 3: Write the command

Write the command file to `.claude/plugins/lup/commands/<command-name>.md`.

**Frontmatter**: Choose `allowed-tools` based on what the investigator needs. Common choices:

- `Read, Grep, Glob` — always needed for code/log exploration
- `Bash(ls:*, wc:*, sort:*, tail:*, stat:*)` — for listing and sizing files
- `Bash(uv run lup-devtools:*)` — if the command needs devtools scripts
- `WebSearch` — if the investigation might need external context
- `AskUserQuestion` — if the investigation might need clarification from the user

**Content**: Write the command body. Use the design from Step 2.

## Step 4: Confirm and iterate

Show the user what was created. Offer to refine it — the first draft is rarely perfect. Use AskUserQuestion to check if anything needs adjustment.

## Rules

- **Read before writing** — Always explore the relevant codebase areas before designing the command. The command should reference actual file paths, actual script names, actual log locations.
- **Be specific** — Generic investigation steps ("search the logs") are useless. Point to specific directories, file patterns, scripts, and code locations.
- **Encode domain knowledge** — The whole point of an investigator command is that it captures knowledge you'd otherwise have to rediscover each time. Bake in common failure modes, known gotchas, and relevant architecture.
- **Keep it conversational** — Use AskUserQuestion when you need input. Don't assume.
