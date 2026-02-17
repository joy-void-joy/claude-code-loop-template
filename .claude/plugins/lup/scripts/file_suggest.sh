#!/bin/bash
# File suggestion provider for Claude Code @ completion.
# Uses git ls-files + fzf for fuzzy matching. Includes refs/ entries.
set -euo pipefail

QUERY=$(jq -r '.query // ""')
cd "${CLAUDE_PROJECT_DIR:-.}"

{
  git --no-pager ls-files
  [ -d refs ] && for d in refs/*/; do [ -L "${d%/}" ] && echo "${d%/}"; done
} | fzf --filter "$QUERY" | head -15
