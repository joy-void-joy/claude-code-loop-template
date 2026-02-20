"""Session history storage and retrieval.

This module handles:
1. Saving session results to notes/traces/<version>/sessions/
2. Loading past sessions for context or analysis (across versions)
3. Tracking session metadata (submitted, outcome, etc.)

The feedback loop scripts read from this storage.

All functions accept :class:`pydantic.BaseModel` instances and work
with raw JSON dicts — no dependency on domain-specific models.
The ``format_history_for_context`` function accepts a pluggable
formatter so downstream projects can display domain-specific fields
without modifying this module.
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lup.lib.paths import iter_session_dirs, sessions_dir

logger = logging.getLogger(__name__)


def save_session(result: BaseModel, *, session_id: str) -> Path:
    """Save a session result to disk.

    Args:
        result: Any Pydantic model representing a session result.
        session_id: Unique session identifier.

    Returns:
        Path to the saved file.
    """
    session_dir = sessions_dir() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = session_dir / f"{timestamp}.json"

    filepath.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Saved session %s to %s", session_id, filepath)

    return filepath


def load_sessions_json(session_id: str) -> list[dict[str, Any]]:
    """Load all session JSON dicts for a given ID across all versions.

    Returns raw dicts rather than typed models, so this function has
    no dependency on domain-specific model classes.

    Args:
        session_id: The session identifier.

    Returns:
        List of session dicts, sorted by timestamp field (oldest first).
    """
    sessions: list[dict[str, Any]] = []

    for session_dir in iter_session_dirs(session_id=session_id):
        for filepath in sorted(session_dir.glob("*.json")):
            try:
                data: dict[str, Any] = json.loads(
                    filepath.read_text(encoding="utf-8")
                )
                sessions.append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load session from %s: %s", filepath, e)

    sessions.sort(key=lambda s: s.get("timestamp", ""))
    return sessions


def get_latest_session_json(session_id: str) -> dict[str, Any] | None:
    """Get the most recent session dict for an ID.

    Args:
        session_id: The session identifier.

    Returns:
        The most recent session dict, or None if no sessions exist.
    """
    sessions = load_sessions_json(session_id)
    return sessions[-1] if sessions else None


def list_all_sessions() -> list[str]:
    """List all session IDs across all versions.

    Returns:
        Sorted, deduplicated list of session IDs.
    """
    from lup.lib.paths import list_all_session_ids

    return list_all_session_ids()


def update_session_metadata(
    session_id: str,
    *,
    outcome: str | None = None,
    submitted_at: str | None = None,
) -> bool:
    """Update metadata for the latest session.

    Args:
        session_id: The session identifier.
        outcome: Outcome value to set (e.g., "success", "failure").
        submitted_at: ISO timestamp when submitted.

    Returns:
        True if a session was updated, False if not found.
    """
    all_files: list[Path] = []
    for session_dir in iter_session_dirs(session_id=session_id):
        all_files.extend(session_dir.glob("*.json"))

    if not all_files:
        return False

    latest_file = sorted(all_files)[-1]

    try:
        data: dict[str, Any] = json.loads(
            latest_file.read_text(encoding="utf-8")
        )

        if outcome is not None:
            data["outcome"] = outcome
        if submitted_at is not None:
            data["submitted_at"] = submitted_at

        latest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Updated metadata for session %s", session_id)
        return True

    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to update session %s: %s", session_id, e)
        return False


# -- Default formatter for format_history_for_context -------------------------


def _default_session_formatter(session: dict[str, Any]) -> str:
    """Format a session dict as a markdown summary.

    Extracts common fields that most domains will have. Downstream
    projects can provide a custom formatter for domain-specific display.
    """
    lines: list[str] = [f"### {session.get('timestamp', 'unknown')}"]

    output = session.get("output", {})
    if isinstance(output, dict):
        if "summary" in output:
            lines.append(f"**Summary**: {str(output['summary'])[:200]}...")
        if "confidence" in output:
            lines.append(f"**Confidence**: {output['confidence']:.1%}")

    if session.get("outcome"):
        lines.append(f"**Outcome**: {session['outcome']}")

    lines.append("")
    return "\n".join(lines)


def format_history_for_context(
    sessions: list[dict[str, Any]],
    *,
    max_sessions: int = 5,
    formatter: Callable[[dict[str, Any]], str] | None = None,
) -> str:
    """Format past sessions as context for the agent.

    Args:
        sessions: List of session dicts (from :func:`load_sessions_json`).
        max_sessions: Maximum number of sessions to include.
        formatter: Callable that formats a single session dict into
            a markdown string. Uses a default formatter if ``None``.

    Returns:
        Markdown-formatted summary of past sessions.
    """
    if not sessions:
        return ""

    fmt = formatter or _default_session_formatter

    lines = ["## Past Sessions\n"]
    for session in sessions[-max_sessions:]:
        lines.append(fmt(session))

    return "\n".join(lines)
