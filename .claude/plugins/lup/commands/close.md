---
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion
description: Check PR review status, merge if approved, and clean up branches
---

# Close PR

Check the review status of the feature branch's PR, merge it if approved, and clean up.

## Process

### 1. Identify the PR

Find the open PR for the current branch:

```bash
CURRENT_BRANCH=$(git branch --show-current)
gh pr list --head "$CURRENT_BRANCH" --state open --json number,title,url
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
3. **Stop here.** Tell the user to fix the issues and re-run `/lup:rebase` to push updates.

**If all reviews are approved (or no reviews yet but checks pass):**

1. Show the PR summary to the user
2. Use AskUserQuestion to confirm the merge
3. If confirmed, proceed to merge and cleanup

### 4. Merge the PR

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

Use `--squash` to create a single merge commit. The `--delete-branch` flag removes the branch on remote automatically.

### 5. Clean up

After merge, clean up local state:

```bash
# Switch to the integration branch worktree and pull the merged changes
cd ../dev
git pull
cd -

# Delete the local feature branch
git branch -D "$CURRENT_BRANCH" 2>/dev/null || true
```

Then warn the user that their current worktree corresponds to the now-merged branch. Suggest they run `/lup:clean-gone` from the dev worktree to remove this worktree, or navigate to the dev worktree to continue working.

### 6. Report

Summarize what was done:

- PR merged (with link)
- Branch deleted (local + remote)
- Remaining cleanup needed (worktree removal if applicable)

## Guidelines

- Always show review comments before merging -- never skip review feedback
- Use `--squash` merge to keep dev history clean
- The user must confirm before merging via AskUserQuestion
