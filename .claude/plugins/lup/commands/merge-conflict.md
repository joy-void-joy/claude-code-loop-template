---
allowed-tools: Bash(git:*), Read, Grep, Glob, Edit, Write, AskUserQuestion
description: Resolve merge conflicts after a failed merge attempt
argument-hint: [context about the merge and priorities]
---

# Resolve Merge Conflicts

Resolve all merge conflicts in the working tree after a failed merge or rebase.

**User-provided context:** $ARGUMENTS

## Process

1. **Assess the situation**:

   ```bash
   # Determine if we're in a merge, rebase, or cherry-pick
   git status

   # List all conflicted files
   git diff --name-only --diff-filter=U
   ```

2. **Understand what this branch does**:
   - Identify which branch is being merged into which
   - Review commits since this branch diverged from the base (max 10):
     ```bash
     # Find the merge base and show branch commits
     git log --oneline $(git merge-base HEAD MERGE_HEAD)..HEAD | head -10
     ```
   - Derive the **branch scope** -- a summary of everything this branch is about. If the branch does multiple things (e.g., "refactors CDF generation, adds new calibration tools, and fixes a test"), list all of them. The scope should cover the full set of intentional changes.
   - Also check the other side to understand what changed there:
     ```bash
     git log --oneline $(git merge-base HEAD MERGE_HEAD)..MERGE_HEAD | head -10
     ```
   - Use the user-provided context above for additional priorities

3. **For each conflicted file**:
   - Read the full file to see all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
   - Understand what each side changed and why by reading the surrounding code
   - Check `git log --oneline -5 -- <file>` on both sides to understand the history
   - **Classify each conflict by branch scope** before resolving (see Resolution Decision Tree below)
   - Remove all conflict markers after resolution

4. **Validate the resolution**:
   - Read each resolved file to confirm no remaining conflict markers
   - Ensure the resolved code is syntactically correct and logically sound
   - Check for duplicate imports, repeated function definitions, or other merge artifacts

5. **Stage and verify**:

   ```bash
   # Stage resolved files
   git add <resolved-files>

   # Verify no conflicts remain
   git diff --name-only --diff-filter=U

   # Show what will be committed
   git diff --cached --stat
   ```

6. **Complete the merge** (only if all conflicts are resolved):

   ```bash
   # For a merge:
   git commit --no-edit

   # For a rebase: git rebase --continue
   # For a cherry-pick: git cherry-pick --continue
   ```

## Resolution Decision Tree

First classify each conflict hunk by **branch scope**, then resolve:

### Step A: Scope classification

Using the branch scope summary from step 2, classify each conflict hunk:

- **In-scope** -- The conflict is in code this branch intentionally changed (matches any part of the branch's purpose). **Take ours** (HEAD) -- this branch is the authority for these changes.
- **Out-of-scope** -- The conflict is in code this branch didn't intentionally modify (unrelated to any of the branch's purposes). **Take theirs** (MERGE_HEAD) -- the other branch has the more intentional changes here.
- **Mixed / ambiguous** -- Both sides made intentional changes to the same code, or you can't confidently classify. Proceed to Step B.

### Step B: Resolve mixed/ambiguous conflicts

For hunks that don't clearly fall into in-scope or out-of-scope:

#### Auto-resolve (no user input needed)

- **Non-overlapping additions** -- Both sides add different new content (imports, functions, config entries). Combine both.
- **Clear superset** -- One side is a strict superset of the other. Take the superset.
- **Whitespace / formatting only** -- Take either side consistently.
- **Identical intent** -- Both sides made the same change with trivially different wording. Take either.

#### Ask the user (use AskUserQuestion)

- **Different approaches** -- Both sides solve the same problem differently. Present both approaches with context and ask which to keep or how to combine.
- **Conflicting deletions vs additions** -- One side removes code the other side modifies. Show what was removed and what was changed, ask which direction to go.
- **Structural reorganization** -- Both sides restructured the same section differently. Present the two structures and ask for preference.
- **Ambiguous priority** -- When you genuinely can't tell which version is better or more complete without domain knowledge the user has.

**When asking, always:**

- **Show the exact conflict** -- Before the AskUserQuestion call, output both versions as labeled code blocks so the user can read the actual content
- Explain what each side was trying to do
- Suggest a recommendation if you have one
- Offer "combine both" as an option when feasible

## General Guidelines

- **Watch for semantic conflicts** -- Even after resolving textual conflicts, check that the combined code makes sense (e.g., a renamed variable on one side but old name used on the other)
- **Check adjacent code** -- Sometimes conflicts reveal that nearby (non-conflicting) code also needs updating for consistency
