---
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion
description: Review branches/worktrees and clean up merged ones
---

# Clean Merged Branches

Review all local branches and worktrees. Identify branches that are fully merged (into main or any other active branch) or have completed PRs. Present the merge graph and ask before deleting.

## Process

1. **Fetch and prune** remote tracking info:
   ```bash
   git fetch --prune
   ```

2. **Inventory** all local branches and worktrees:
   ```bash
   git branch -vv
   git worktree list
   ```

3. **Check containment** — for every pair of branches, check if one is an ancestor of another:
   ```bash
   git merge-base --is-ancestor <branch> <target>
   ```
   A branch is "consumed" if it's fully contained in main OR any other active branch (not just main).

4. **Check PR status** for branches that aren't ancestors of anything:
   ```bash
   gh pr list --state all --json number,title,headRefName,state,mergedAt
   ```
   A branch is also deletable if:
   - It has a merged PR (direct or via a `-rebase` suffix branch)
   - Its corresponding rebase branch's PR was merged (content reached main through rebased commits)

5. **Detect transitive merges** — for branches still unresolved after steps 3-4, check if their content reached main through an intermediate branch that was rebased:
   ```bash
   # Find all merged PR branches
   # For each unresolved branch B, check if B is an ancestor of any merged PR branch
   git merge-base --is-ancestor <B> <merged-pr-branch>
   ```
   Walk the merge graph: if branch B is an ancestor of branch X, and X (or X-rebase) has a merged PR into main, then B's content reached main transitively — even though B itself isn't an ancestor of main (because X was rebased before merging).

   Also check for branches that were **branched from** an intermediate branch and have since been superseded:
   ```bash
   # Check unique commits remaining after cherry-pick filtering
   git log --oneline --cherry-pick --left-only <B>...main | wc -l
   # Check actual code diff (ignoring data/notes)
   git diff <B> main --stat -- src/ .claude/ tests/
   ```
   If the branch has few unique commits and minimal source code diff vs main, it's **stale** (superseded by main's continued development, even if not literally merged).

6. **Categorize** each branch:
   - **DELETE** — fully contained in another branch, or PR merged
   - **STALE** — content reached main transitively (via rebased intermediate branch) or branch is superseded by main's continued development. Recommend deletion but flag the transitive path.
   - **KEEP** — has unique commits not captured elsewhere, or has an open PR
   - **CURRENT** — the branch we're on (never delete, warn if it qualifies)

7. **Present the merge graph** showing:
   - Which branches are contained in which
   - PR status for each branch
   - Which have worktrees
   - Proposed action (DELETE/STALE/KEEP) with reason
   - For STALE branches, show the transitive path
   - Format as a table for DELETE/STALE candidates and a tree for the merge flow

8. **Confirm with user** via AskUserQuestion before deleting anything.

9. **Remove worktrees first** (if any):
   ```bash
   git worktree remove <path>
   ```

10. **Delete branches**:
    ```bash
    git branch -d <branch-name>
    ```
    Use `-d` (not `-D`). If `-d` fails (branch not recognized as merged due to rebase), report to user and ask if `-D` is acceptable.

11. **Delete remote branches** if they still exist:
    ```bash
    git push origin --delete <branch-name>
    ```

12. **Report results**: List what was cleaned up.

## Guidelines

- Never force-delete (`-D`) without explicit user approval for that specific branch
- Always confirm before deleting anything
- Skip the current branch — warn the user instead
- A branch merged into ANY other active branch counts as consumed (not just main)
- For rebased branches: the original feature branch content is in main via the rebase PR, even though `--is-ancestor` returns false (commits were rewritten)
