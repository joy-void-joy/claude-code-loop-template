---
allowed-tools: Read, Grep, Glob, Bash(ls:*, wc:*, sort:*, tail:*, stat:*)
description: Trace an error through logs to find root cause
argument-hint: [error message or fragment]
---

# Debug: Trace an Error

**Do not hypothesize -- trace.** Find the actual logs, read the exact exception, and report what happened. Never list "likely causes" or suggest the user check things.

## Input

**Error text**: $ARGUMENTS

## Process

### 1. Search logs for the error

Search `logs/` for the error text (or a distinctive fragment of it). Use Grep with the most specific substring from the error -- avoid generic words like "error" or "failed" when more specific text is available.

```
# Example: search for a distinctive error fragment
Grep(pattern="<distinctive part of error>", path="logs/", output_mode="content", context=10)
```

If the error text is too long for a single grep, extract the most distinctive phrase (e.g., an exception class name, a specific message, a status code with context).

### 2. Find the right log file

If multiple log files match, identify the **most recent** one (logs are named by timestamp: `YYYYMMDD-HHMMSS.log` or `YYYYMMDD_HHMMSS.log`).

If no matches found in `logs/`:
- Try `notes/sessions/` for meta-reflections mentioning the error
- Try broader search terms (exception class name, HTTP status code)
- If still nothing: report exactly what was searched and that no logs contain this error. State what logging would need to be added and where.

### 3. Read the full context

Once you find the log file containing the error:

1. **Read the traceback** -- Find the full exception chain. Read 50-100 lines around the error to see the complete traceback and what led to it.
2. **Trace backwards** -- What was the agent doing when the error occurred? Read earlier in the log to find the tool call or action that triggered it.
3. **Check the source** -- Use Read/Grep to find the exact line in the source code (`src/`) where the exception was raised or where the failing logic lives.

### 4. Report findings

Structure your report as:

**What happened:**
- The exact exception/error (quote the traceback)
- Which file and line in the source code

**Why it happened:**
- What the agent was doing at the time (from the log context)
- The chain of events that led to the error

**How to fix it:**
- Specific code changes needed (show the code, point to the file and line)

**If logs are insufficient:**
- State exactly what logging to add and where, so the error is captured next time
- Be specific: "Add `logger.exception(...)` at `src/loop/agent/core.py:42` inside the `except` block"

## Rules

- **Never guess.** If you can't find the error in the logs, say so. Don't speculate about what might have caused it.
- **Quote exactly.** Show the actual traceback and log lines, not paraphrased summaries.
- **Read the source.** After finding the error location, read the actual source code to understand the failure.
- **Be specific about fixes.** Point to exact files and lines, show before/after code.
