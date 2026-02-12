"""Session history storage and retrieval.

This module handles:
1. Saving session results to notes/sessions/
2. Loading past sessions for context or analysis
3. Tracking session metadata (submitted, outcome, etc.)

The feedback loop scripts read from this storage.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from lup.agent.models import SessionResult

logger = logging.getLogger(__name__)

# Base path for session storage
SESSIONS_PATH = Path("./notes/sessions")


def save_session(result: SessionResult) -> Path:
    """Save a session result to disk.

    Args:
        result: The session result to save.

    Returns:
        Path to the saved file.
    """
    session_dir = SESSIONS_PATH / result.session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = session_dir / f"{timestamp}.json"

    filepath.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Saved session %s to %s", result.session_id, filepath)

    return filepath


def load_sessions(session_id: str) -> list[SessionResult]:
    """Load all sessions for a given ID.

    Args:
        session_id: The session identifier.

    Returns:
        List of SessionResult objects, sorted by timestamp (oldest first).
    """
    session_dir = SESSIONS_PATH / session_id

    if not session_dir.exists():
        return []

    sessions = []
    for filepath in sorted(session_dir.glob("*.json")):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            sessions.append(SessionResult.model_validate(data))
        except Exception as e:
            logger.warning("Failed to load session from %s: %s", filepath, e)

    return sessions


def get_latest_session(session_id: str) -> SessionResult | None:
    """Get the most recent session for an ID.

    Args:
        session_id: The session identifier.

    Returns:
        The most recent SessionResult, or None if no sessions exist.
    """
    sessions = load_sessions(session_id)
    return sessions[-1] if sessions else None


def list_all_sessions() -> list[str]:
    """List all session IDs.

    Returns:
        List of session IDs (directory names).
    """
    if not SESSIONS_PATH.exists():
        return []

    return [d.name for d in SESSIONS_PATH.iterdir() if d.is_dir()]


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
    session_dir = SESSIONS_PATH / session_id

    if not session_dir.exists():
        return False

    # Find the latest session file
    session_files = sorted(session_dir.glob("*.json"))
    if not session_files:
        return False

    latest_file = session_files[-1]

    try:
        data = json.loads(latest_file.read_text(encoding="utf-8"))

        if outcome is not None:
            data["outcome"] = outcome
        if submitted_at is not None:
            data["submitted_at"] = submitted_at

        latest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Updated metadata for session %s", session_id)
        return True

    except Exception as e:
        logger.warning("Failed to update session %s: %s", session_id, e)
        return False


def format_history_for_context(
    sessions: list[SessionResult], max_sessions: int = 5
) -> str:
    """Format past sessions as context for the agent.

    Args:
        sessions: List of past sessions.
        max_sessions: Maximum number of sessions to include.

    Returns:
        Markdown-formatted summary of past sessions.
    """
    if not sessions:
        return ""

    lines = ["## Past Sessions\n"]

    for session in sessions[-max_sessions:]:
        lines.append(f"### {session.timestamp}")
        lines.append(f"**Confidence**: {session.output.confidence:.1%}")
        lines.append(f"**Summary**: {session.output.summary[:200]}...")

        if hasattr(session, "outcome") and session.outcome:
            lines.append(f"**Outcome**: {session.outcome}")

        lines.append("")

    return "\n".join(lines)
