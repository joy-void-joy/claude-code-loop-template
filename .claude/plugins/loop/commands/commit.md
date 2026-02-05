---
allowed-tools: Bash, Read, Glob, Grep
description: Review all diffs and create atomic commits
---

# Create Commits

Review all uncommitted changes and create well-structured atomic commits.

## Your Task

Create commits for all staged and unstaged changes, following conventional commit format.

## Phase 1: Assess Changes

Run these commands in parallel:
1. `git status` - See all changed files
2. `git diff` - See unstaged changes
3. `git diff --cached` - See staged changes
4. `git log --oneline -10` - See recent commit style

## Phase 2: Group Changes

Analyze the changes and group them into logical commits:

- **One logical change per commit**: If changes serve different purposes, split them
- **Related files together**: Changes to a module and its tests go together
- **Order matters**: Earlier commits should not depend on later ones

## Phase 3: Create Commits

For each group:

1. Stage the relevant files: `git add <files>`
2. Create the commit with conventional format:

```bash
git commit -m "$(cat <<'EOF'
type(scope): description

Optional body with more details.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Commit Types

- `feat` — New feature or capability
- `fix` — Bug fix
- `refactor` — Code restructuring without behavior change
- `docs` — Documentation only
- `test` — Adding or updating tests
- `chore` — Maintenance (deps, config)
- `meta` — Changes to `.claude/` files
- `data` — Generated outputs

### Examples

```
feat(agent): add retry logic for API calls
fix(tools): handle empty response from search
refactor(config): extract settings validation
meta(claude): add new workflow command
```

## Phase 4: Verify

After creating commits:
1. Run `git log --oneline -5` to show what was created
2. Run `git status` to confirm working directory is clean

## Guidelines

- **Never amend** unless explicitly requested
- **Never force push** to main/master
- **Don't skip hooks** unless explicitly requested
- **Don't commit secrets** (.env.local, credentials, API keys)
- **Don't commit large binaries** unless necessary

## If Pre-commit Hooks Fail

1. Fix the issue (formatting, linting, etc.)
2. Re-stage the fixed files
3. Create a **new** commit (don't amend - the previous commit didn't happen)
