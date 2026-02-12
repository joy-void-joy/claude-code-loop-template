---
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
description: Create a clean rebase with atomic commits and open a PR
---

# Rebase and PR

Clean up commit history into meaningful atomic commits and create a pull request.

## Your Task

1. Analyze the current branch's commits
2. Propose a clean commit structure
3. Create a rebase plan
4. Execute the rebase
5. Open a PR

## Phase 1: Analyze Current State

Run in parallel:
1. `git log --oneline main..HEAD` - Commits to rebase
2. `git diff main..HEAD --stat` - Files changed
3. `git log main..HEAD --format="%s%n%b%n---"` - Full commit messages

## Phase 2: Propose Structure

Based on the changes, propose a clean commit structure:

- **Group related changes**: Module + tests together
- **Logical order**: Base changes before dependent changes
- **Meaningful messages**: Each commit tells a story
- **Atomic commits**: Each could be reverted independently

Use AskUserQuestion to propose the structure:

```
I found N commits that could be reorganized into:

1. feat(scope): description
   - file1.py
   - file2.py

2. test(scope): add tests for feature
   - test_file.py

3. docs(scope): update documentation
   - README.md

Does this structure look good?
```

## Phase 3: Execute Rebase

**WARNING**: Rebasing rewrites history. Confirm with user before proceeding.

### Option A: Simple squash
If all commits should become one:
```bash
git reset --soft main
git commit -m "message"
```

### Option B: Interactive reorganization
For complex restructuring, guide the user through:
1. `git rebase -i main`
2. Reorder/squash/edit as needed
3. Resolve any conflicts

### Option C: Fresh commits
If history is too messy:
1. `git diff main > changes.patch`
2. `git checkout main`
3. `git checkout -b clean-branch`
4. Apply changes in logical groups

## Phase 4: Push and PR

1. Force push to remote (with confirmation):
   ```bash
   git push -u origin HEAD --force-with-lease
   ```

2. Create PR:
   ```bash
   gh pr create --title "title" --body "$(cat <<'EOF'
   ## Summary
   - Bullet points

   ## Test plan
   - [ ] How to test

   🤖 Generated with Claude Code
   EOF
   )"
   ```

## Guidelines

- **Never rebase main/master**
- **Confirm before force push**
- **Use --force-with-lease** not --force
- **Keep meaningful history**: Don't squash everything into one commit
- **Write good messages**: Future you will thank present you

## PR Template

```markdown
## Summary
<1-3 bullet points describing the change>

## Changes
- List of specific changes

## Test plan
- [ ] How to verify this works

🤖 Generated with Claude Code
```
