---
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
argument-hint: [target-branch]
description: Clean up commit history on the feature branch and open/update a PR
---

# Rebase and PR

Clean up the commit history on the current feature branch, push it, and open (or update) a PR.

## Determine Branches

### Base branch (`<base>`)

Auto-detect the base branch -- the branch this feature branch diverged from. For each local branch, find the merge-base with HEAD; the branch whose merge-base is closest to HEAD (fewest commits between merge-base and HEAD) is the parent. Exclude the current branch itself.

If auto-detection is ambiguous or no clear parent is found, use `AskUserQuestion` to ask which branch to use as base.

### PR target (`<target>`)

If a target branch was provided as an argument, use it as the PR target. Otherwise, `<target>` defaults to `<base>`.

**Scope:** Only rebase changes since the branch diverged from `<base>`. Do not touch commits that already exist on `<base>`.

## Pre-rebase Validation

Before starting the rebase, ensure the branch is clean and passing all checks.

1. **Merge local settings into shared config**:
   Check if `.claude/settings.local.json` exists. If it does, review it and merge all sensible settings into `.claude/settings.json` — including permissions (allow/deny/ask rules), auto-accept patterns, and any other configuration that would benefit all contributors. Skip anything user-specific (e.g., personal paths, tokens). Commit the settings update as a separate commit.

2. **Merge `<base>` into feature branch**:
   ```bash
   # Update local <base> and merge into feature branch
   cd ../<base>
   git pull
   git push
   cd -
   git merge <base>
   ```
   Resolve any merge conflicts before proceeding. This ensures the branch is up-to-date.

3. **Run all checks**:
   ```bash
   uv run pyright
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest
   ```
   Fix any issues found. The rebased branch should only contain passing code.

4. **Read PLAN.md** (if it exists):
   Check if the branch has a PLAN.md. If it does, read it and verify:
   - All planned items are either completed (`[x]`) or explicitly deferred
   - No items are marked in-progress (`[~]`)
   - The plan reflects what was actually built

   If there are incomplete items, use AskUserQuestion to confirm whether to proceed or address them first.

## Process

1. **Sync `<base>` with remote**:
   ```bash
   cd ../<base>
   git pull
   git push
   cd -
   ```
   Ensure local `<base>` is up-to-date before rebasing.

2. **Push and open PR** (if not already open):

   Push the feature branch:
   ```bash
   git push -u origin <branch>
   ```

   Check if a PR already exists:
   ```bash
   gh pr list --head "<branch>" --base "<target>" --state open --json number,url
   ```

   **If no PR exists** (first run):
   ```bash
   gh pr create --base "<target>" --title "<conventional commit style title>" --body "$(cat <<'EOF'
   ## Summary
   <1-3 bullet points describing the changes>
   EOF
   )"
   ```

   **If a PR already exists**, skip this step — we'll force-push the cleaned history later.

3. **Gather context**:
   - Identify the current branch and confirm `<base>`
   - Review the full diff from base to HEAD: `git diff <base>...HEAD`
   - List existing commits: `git log --oneline <base>..HEAD`

4. **Understand all changes**:
   - Read the changed files to understand the complete set of modifications
   - Think about what logical units of work exist (features, refactors, fixes, tests, docs)
   - **Ignore the existing commit history** — focus on what makes sense as a clean sequence

5. **Reset and rebuild commits**:

   Reset all commits back to staged changes:
   ```bash
   git reset --soft <base>
   ```

   Now all changes are staged. For each logical unit of work:
   - Selectively unstage with `git reset HEAD <files>`, then stage and commit the relevant pieces
   - Or use `git commit` with specific files to build atomic commits
   - Order commits logically (dependencies first, then features, then polish)
   - Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

6. **Force push to update the PR**:
   ```bash
   git push --force
   ```

   Return the PR URL to the user when done. Include a commit list in the PR body:
   ```bash
   gh pr edit <PR_NUMBER> --body "$(cat <<'EOF'
   ## Summary
   <1-3 bullet points describing the changes>

   ## Commits
   <list of commits in the rebased branch>

   ## Test plan
   - [ ] How to verify this works
   EOF
   )"
   ```

## Guidelines

- **Never rebase dev/main/master**
- **Confirm before force push**
- **Use --force** (not --force-with-lease) — after `git reset --soft`, the local ref diverges from remote in a way that --force-with-lease rejects. Plain --force is correct since this command intentionally rewrites history.
- **Keep meaningful history**: Don't squash everything into one commit
- **Write good messages**: Future you will thank present you
