"""Centralized path constants and helpers for agent session data.

All session-related paths are routed through this module. Writers use
version-specific directories; readers iterate across all versions.

Paths auto-detect the project root (walking up to ``pyproject.toml``)
but can be overridden via :func:`configure`::

    from lup.lib.paths import configure
    configure(root=Path("/my/project"), notes_dir=Path("/my/data/notes"))

Layout:
    notes/traces/<version>/sessions/<session_id>/<timestamp>.json
    notes/traces/<version>/outputs/<task_id>/<timestamp>/
    notes/traces/<version>/logs/<session_id>/<timestamp>.md
    notes/scores.csv
    notes/feedback_loop/
"""

import logging
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from lup.version import AGENT_VERSION

logger = logging.getLogger(__name__)


def _find_project_root() -> Path:
    """Find project root by walking up to pyproject.toml."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


# -- Mutable path state -------------------------------------------------------
# Auto-detected on first import; overridable via configure().

_project_root = _find_project_root()
_notes_path = _project_root / "notes"
_runtime_logs_path = _project_root / "logs"


def configure(
    *,
    root: Path | None = None,
    notes_dir: Path | None = None,
    logs_dir: Path | None = None,
) -> None:
    """Override auto-detected paths.

    Call before any session operations. All derived paths
    (``traces_path``, ``feedback_path``, ``scores_csv_path``, etc.)
    update automatically since they read from these values.

    Args:
        root: Project root directory. Resets ``notes_dir`` and
            ``logs_dir`` to ``root/notes`` and ``root/logs`` unless
            they are also specified.
        notes_dir: Override notes directory independently.
        logs_dir: Override runtime logs directory independently.
    """
    global _project_root, _notes_path, _runtime_logs_path  # noqa: PLW0603

    if root is not None:
        _project_root = root
        _notes_path = root / "notes"
        _runtime_logs_path = root / "logs"

    if notes_dir is not None:
        _notes_path = notes_dir
    if logs_dir is not None:
        _runtime_logs_path = logs_dir


# -- Public path accessors ----------------------------------------------------


def project_root() -> Path:
    """Return the project root directory."""
    return _project_root


def notes_path() -> Path:
    """Return the notes directory (``<root>/notes`` by default)."""
    return _notes_path


def runtime_logs_path() -> Path:
    """Return the runtime logs directory (``<root>/logs`` by default)."""
    return _runtime_logs_path


def traces_path() -> Path:
    """Return ``notes/traces/``."""
    return _notes_path / "traces"


def feedback_path() -> Path:
    """Return ``notes/feedback_loop/``."""
    return _notes_path / "feedback_loop"


def scores_csv_path() -> Path:
    """Return ``notes/scores.csv``."""
    return _notes_path / "scores.csv"


# -- Timestamp helpers --------------------------------------------------------

_TIMESTAMP_FMT = "%Y%m%d_%H%M%S"
_TIMESTAMP_RE = re.compile(r"\d{8}_\d{6}")


def parse_timestamp(name: str) -> datetime:
    """Parse the last YYYYMMDD_HHMMSS occurrence from a filename or string."""
    matches = _TIMESTAMP_RE.findall(Path(name).stem)
    if not matches:
        raise ValueError(f"No YYYYMMDD_HHMMSS timestamp found in: {name}")
    return datetime.strptime(matches[-1], _TIMESTAMP_FMT)


# -- Write paths (version-specific) ------------------------------------------


def sessions_dir(version: str = AGENT_VERSION) -> Path:
    """Directory for session JSONs: notes/traces/<version>/sessions/"""
    return traces_path() / version / "sessions"


def outputs_dir(version: str = AGENT_VERSION) -> Path:
    """Directory for agent outputs: notes/traces/<version>/outputs/"""
    return traces_path() / version / "outputs"


def trace_logs_dir(version: str = AGENT_VERSION) -> Path:
    """Directory for reasoning logs: notes/traces/<version>/logs/"""
    return traces_path() / version / "logs"


# -- Read paths (cross-version iteration) -------------------------------------


def _version_dirs() -> list[Path]:
    """Return all version directories under notes/traces/, sorted."""
    tp = traces_path()
    if not tp.exists():
        return []
    return sorted(d for d in tp.iterdir() if d.is_dir() and not d.name.startswith("."))


def iter_session_dirs(
    session_id: str | None = None,
    version: str | None = None,
) -> Iterator[Path]:
    """Iterate over session directories across all (or filtered) versions.

    Yields paths like: notes/traces/0.1.0/sessions/my-session/
    """
    ver_dirs = [traces_path() / version] if version else _version_dirs()

    for ver_dir in ver_dirs:
        sessions_base = ver_dir / "sessions"
        if not sessions_base.exists():
            continue
        if session_id is not None:
            candidate = sessions_base / session_id
            if candidate.exists() and candidate.is_dir():
                yield candidate
        else:
            for d in sessions_base.iterdir():
                if d.is_dir():
                    yield d


def iter_output_dirs(
    task_id: str | None = None,
    version: str | None = None,
) -> Iterator[Path]:
    """Iterate over output directories across all (or filtered) versions.

    Yields paths like: notes/traces/0.1.0/outputs/my-task/
    """
    ver_dirs = [traces_path() / version] if version else _version_dirs()

    for ver_dir in ver_dirs:
        outputs_base = ver_dir / "outputs"
        if not outputs_base.exists():
            continue
        if task_id is not None:
            candidate = outputs_base / task_id
            if candidate.exists() and candidate.is_dir():
                yield candidate
        else:
            for d in outputs_base.iterdir():
                if d.is_dir():
                    yield d


def iter_trace_log_files(session_id: str | None = None) -> Iterator[Path]:
    """Iterate reasoning log files across all versions."""
    for ver_dir in _version_dirs():
        logs_base = ver_dir / "logs"
        if not logs_base.exists():
            continue
        if session_id is not None:
            session_logs = logs_base / session_id
            if session_logs.exists():
                yield from session_logs.glob("*.md")
        else:
            yield from logs_base.rglob("*.md")


def list_all_session_ids(version: str | None = None) -> list[str]:
    """Return all session IDs across versions, deduplicated."""
    ids: set[str] = set()
    for d in iter_session_dirs(version=version):
        ids.add(d.name)
    return sorted(ids)
