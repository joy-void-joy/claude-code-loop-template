"""RO/RW notes directory structure for agent sessions.

This is a TEMPLATE. Customize the directory structure for your domain.

Key patterns:
1. Explicit separation of RW (session can write) and RO (historical, read-only)
2. Session-specific directories prevent cross-session pollution
3. Logs directory is NOT accessible to agent (for feedback loop only)
4. Permission hooks enforce the access control

Usage:
    from lup.lib import setup_notes, NotesConfig

    notes = setup_notes(session_id="12345", task_id="my-task")
    # notes.rw = directories agent can write to
    # notes.ro = directories agent can only read
    # notes.trace_log = where to save trace (agent can't read this)
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lup.lib.paths import RUNTIME_LOGS_PATH, outputs_dir, sessions_dir, trace_logs_dir


class NotesConfig(BaseModel):
    """Notes folder configuration with explicit RW/RO separation.

    Customize the fields for your domain's directory structure.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: Path = Field(description="This session's working directory")
    output: Path = Field(description="Where this session saves its outputs")
    trace_log: Path = Field(description="Trace log path (agent cannot access)")
    rw: list[Path] = Field(default_factory=list, description="Read-write directories")
    ro: list[Path] = Field(default_factory=list, description="Read-only directories")

    @property
    def all_dirs(self) -> list[Path]:
        """All directories the agent can access (RW + RO)."""
        return self.rw + self.ro


def setup_notes(
    session_id: str,
    task_id: str | None = None,
) -> NotesConfig:
    """Create session-specific notes folder structure.

    Uses version-aware paths from lup.lib.paths. The structure separates:
    - RW directories: This session can write here
    - RO directories: Historical data, read-only for this session
    - Logs: Agent cannot access (for feedback loop analysis)

    Customize this function for your domain's directory needs.

    Args:
        session_id: Unique session identifier.
        task_id: Optional task identifier (for organizing by task).

    Returns:
        NotesConfig with RW and RO directories separated.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Session-specific paths (RW) -- versioned
    session_path = sessions_dir() / session_id
    output_path = outputs_dir() / (task_id or session_id) / timestamp

    # Create directories
    session_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    RUNTIME_LOGS_PATH.mkdir(parents=True, exist_ok=True)

    # Trace log file (agent cannot access logs/)
    trace_log = trace_logs_dir() / session_id / f"{timestamp}.md"
    trace_log.parent.mkdir(parents=True, exist_ok=True)

    return NotesConfig(
        session=session_path,
        output=output_path,
        trace_log=trace_log,
        rw=[session_path, output_path],
        ro=[outputs_dir().parent],  # Read all versioned output dirs
    )


def path_is_under(file_path: str | Path, allowed_dirs: list[Path]) -> bool:
    """Check if a file path is under one of the allowed directories.

    Used by permission hooks to enforce RW/RO access.

    Args:
        file_path: Path to check.
        allowed_dirs: List of allowed parent directories.

    Returns:
        True if the path is under one of the allowed directories.
    """
    try:
        path = Path(file_path).resolve()
    except (OSError, ValueError):
        return False

    for allowed in allowed_dirs:
        try:
            path.relative_to(allowed.resolve())
            return True
        except ValueError:
            continue
    return False
