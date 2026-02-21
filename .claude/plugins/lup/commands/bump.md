---
allowed-tools: Bash(git:*), Bash(uv:*), Read, Grep, Glob, AskUserQuestion
description: Review changes since last bump and bump agent version
argument-hint: [patch|minor|major]
---

# Version Bump

Review changes since the last version bump and bump `AGENT_VERSION` accordingly.

## Input

**Bump level** (optional): $ARGUMENTS

If no level is provided, determine the appropriate level from the changes.

## Process

### 1. Gather context

Run these in parallel:

- Read `src/lup/version.py` to get the current version
- Run `git tag --list 'v*' --sort=-version:sort` to find the latest version tag
- Run `git log --oneline` (limited to last 50 commits) to see recent history

### 2. Find changes since last bump

Using the latest version tag (e.g., `v1.1.0`):

- Run `git log --oneline <tag>..HEAD` to see all commits since the last bump
- Run `git diff --stat <tag>..HEAD` to see which files changed

If no version tag exists, use the commit that last modified `src/lup/version.py`:

- `git log -1 --format=%H -- src/lup/version.py`

### 3. Classify changes

Read through the commits and categorize them:

- **Behavior changes** (require a bump): prompt changes, new/modified tools, scoring logic, subagent changes
- **Data changes** (no bump needed): session outputs, notes, resolution updates
- **Infrastructure changes** (no bump needed): dependencies, CI, scripts, CLAUDE.md

If there are NO behavior changes since the last bump, inform the user and stop — no bump is needed.

### 4. Determine bump level

Apply the bump rules from `src/lup/version.py`:

| Level     | When                                          | Examples                                     |
| --------- | --------------------------------------------- | -------------------------------------------- |
| **patch** | Bug fixes, config tweaks, tool fixes          | Fixed API error handling, adjusted timeout   |
| **minor** | Prompt changes, new tools, tool modifications | Added web search tool, rewrote system prompt |
| **major** | Architecture changes                          | New LLM, new framework, fundamental redesign |

If the user provided a level in `$ARGUMENTS`, use it. Otherwise, recommend a level based on the changes and confirm with `AskUserQuestion`.

### 5. Bump the version

Update `src/lup/version.py` with the new version string. For example, if the current version is `0.1.0` and the bump level is `minor`, the new version is `0.2.0`.

### 6. Create git tag

```bash
git tag v<new_version>
```

### 7. Verify and report

- Read the updated `src/lup/version.py` to confirm the new version
- Show the user what was bumped and the behavioral changes that warranted the bump

## Guidelines

- **Only bump for behavior changes** — Data, docs, and infra commits don't warrant a bump
- **Summarize what changed for the agent**, not for the codebase — focus on how agent behavior differs
- **When in doubt, ask** — Use AskUserQuestion if the level is ambiguous
