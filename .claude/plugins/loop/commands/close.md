---
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion
description: Check PR review status, merge if approved, and clean up branches
---

# Close PR

Check the review status of a rebase PR, merge it if approved, and clean up all related branches and worktrees.

## Process

### 1. Identify the PR

Determine the current branch and find its associated `-rebase` PR:

```bash
CURRENT_BRANCH=$(git branch --show-current)
REBASE_BRANCH="${CURRENT_BRANCH}-rebase"
```

Find the open PR for the rebase branch:

```bash
gh pr list --head "$REBASE_BRANCH" --state open --json number,title,url
```

If no PR is found, check if the user passed a PR number as an argument. If still nothing, report the error and stop.

### 2. Check PR review status

Fetch the PR's review state and comments:

```bash
# Get PR status: checks, reviews, merge state
gh pr view <PR_NUMBER> --json reviews,statusCheckRollup,mergeable,mergeStateStatus,reviewDecision

# Get review comments (the detailed feedback)
gh pr view <PR_NUMBER> --comments
```

### 3. Evaluate and act

**If there are unresolved review comments or requested changes:**

1. Display all review comments to the user, clearly formatted
2. Show which reviews requested changes vs approved
3. **Stop here.** Tell the user to fix the issues and re-run `/loop:rebase` to push updates.

**If all reviews are approved (or no reviews yet but checks pass):**

1. Show the PR summary to the user
2. Use AskUserQuestion to confirm the merge
3. If confirmed, proceed to merge and cleanup

### 4. Merge the PR

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

Use `--squash` to create a single merge commit. The `--delete-branch` flag removes the rebase branch on remote automatically.

### 5. Clean up

After merge, clean up local state:

```bash
# Switch to main worktree and pull the merged changes
cd ../main
git pull
cd -

# Delete the local rebase branch (if it exists locally)
git branch -d "$REBASE_BRANCH" 2>/dev/null || true

# Delete the original feature branch locally
# Use -D (force): the base branch has merge commits that diverge from main's
# rebased history, so -d always fails. This is expected and safe since the
# PR is merged.
git branch -D "$CURRENT_BRANCH" 2>/dev/null || true

# Delete the original feature branch on remote
git push origin --delete "$CURRENT_BRANCH" 2>/dev/null || true
```

Then warn the user that their current worktree corresponds to the now-merged branch. Suggest they run `/commit-commands:clean-gone` from the main worktree to remove this worktree, or navigate to the main worktree to continue working.

### 6. Report

Summarize what was done:
- PR merged (with link)
- Branches deleted (list which)
- Remaining cleanup needed (worktree removal if applicable)

## Guidelines

- Always show review comments before merging -- never skip review feedback
- Use `--squash` merge to keep main history clean
- Use `-d` for the rebase branch (should be fully merged). Use `-D` for the base branch -- its merge commits always diverge from main's rebased history, so `-d` fails even though the work is merged.
- The user must confirm before merging via AskUserQuestion
- If the current branch IS the rebase branch (not the original), adapt the cleanup accordingly
