"""Centralized path constants and helpers for agent session data.

All session-related paths are routed through this module. Writers use
version-specific directories; readers default to the current AGENT_VERSION
with progressive semver fallback when data is insufficient.

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


def find_project_root() -> Path:
    """Find project root by walking up to pyproject.toml."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


# -- Mutable path state -------------------------------------------------------
# Auto-detected on first import; overridable via configure().

PROJECT_ROOT = find_project_root()
NOTES_DIR = PROJECT_ROOT / "notes"
RUNTIME_LOGS_DIR = PROJECT_ROOT / "logs"


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
    global PROJECT_ROOT, NOTES_DIR, RUNTIME_LOGS_DIR  # noqa: PLW0603

    if root is not None:
        PROJECT_ROOT = root
        NOTES_DIR = root / "notes"
        RUNTIME_LOGS_DIR = root / "logs"

    if notes_dir is not None:
        NOTES_DIR = notes_dir
    if logs_dir is not None:
        RUNTIME_LOGS_DIR = logs_dir


# -- Public path accessors ----------------------------------------------------


def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


def notes_path() -> Path:
    """Return the notes directory (``<root>/notes`` by default)."""
    return NOTES_DIR


def runtime_logs_path() -> Path:
    """Return the runtime logs directory (``<root>/logs`` by default)."""
    return RUNTIME_LOGS_DIR


def traces_path() -> Path:
    """Return ``notes/traces/``."""
    return NOTES_DIR / "traces"


def feedback_path() -> Path:
    """Return ``notes/feedback_loop/``."""
    return NOTES_DIR / "feedback_loop"


def scores_csv_path() -> Path:
    """Return ``notes/scores.csv``."""
    return NOTES_DIR / "scores.csv"


# -- Timestamp helpers --------------------------------------------------------

TIMESTAMP_FMT = "%Y%m%d_%H%M%S"
TIMESTAMP_RE = re.compile(r"\d{8}_\d{6}")


def parse_timestamp(name: str) -> datetime:
    """Parse the last YYYYMMDD_HHMMSS occurrence from a filename or string."""
    matches = TIMESTAMP_RE.findall(Path(name).stem)
    if not matches:
        raise ValueError(f"No YYYYMMDD_HHMMSS timestamp found in: {name}")
    return datetime.strptime(matches[-1], TIMESTAMP_FMT)


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


def version_dirs() -> list[Path]:
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
    ver_dirs = [traces_path() / version] if version else version_dirs()

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
    ver_dirs = [traces_path() / version] if version else version_dirs()

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
    for ver_dir in version_dirs():
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


# -- Version scope resolution ------------------------------------------------

MIN_VERSION_DATAPOINTS = 10

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_semver(version: str) -> tuple[int, int, int] | None:
    """Parse 'X.Y.Z' into (major, minor, patch), or None if invalid."""
    m = _SEMVER_RE.match(version)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def count_sessions_for_versions(versions: list[str]) -> int:
    """Count total session directories across a set of version directories."""
    return sum(sum(1 for _ in iter_session_dirs(version=v)) for v in versions)


def resolve_version(
    version: str | None,
    all_versions: bool = False,
    min_datapoints: int = MIN_VERSION_DATAPOINTS,
) -> tuple[list[str] | None, str | None]:
    """Resolve effective version scope with progressive semver fallback.

    Fallback chain: exact version → X.Y.* → X.* → all versions.
    Widens when the narrower scope has fewer than ``min_datapoints`` sessions.

    Returns ``(version_list, warning_message)``.
    ``version_list`` is ``None`` when all versions should be included.
    """
    if all_versions:
        return None, None

    effective = version if version is not None else AGENT_VERSION
    semver = parse_semver(effective)
    available = [d.name for d in version_dirs()]

    # Level 1: exact version
    exact = [effective] if effective in available else []
    exact_count = count_sessions_for_versions(exact)
    if exact_count >= min_datapoints:
        return exact, None

    if semver is None:
        return None, (
            f"v{effective} has only {exact_count} sessions "
            f"(need {min_datapoints}) — including all versions"
        )

    major, minor, _ = semver

    # Level 2: same minor (X.Y.*)
    minor_matches = [
        v
        for v in available
        if (sv := parse_semver(v)) is not None and sv[0] == major and sv[1] == minor
    ]
    minor_count = count_sessions_for_versions(minor_matches)
    if minor_count >= min_datapoints:
        return minor_matches, (
            f"v{effective} has only {exact_count} sessions "
            f"— widening to v{major}.{minor}.* ({minor_count} sessions)"
        )

    # Level 3: same major (X.*)
    major_matches = [
        v for v in available if (sv := parse_semver(v)) is not None and sv[0] == major
    ]
    major_count = count_sessions_for_versions(major_matches)
    if major_count >= min_datapoints:
        return major_matches, (
            f"v{major}.{minor}.* has only {minor_count} sessions "
            f"— widening to v{major}.* ({major_count} sessions)"
        )

    # Level 4: all versions
    return None, (
        f"v{major}.* has only {major_count} sessions "
        f"(need {min_datapoints}) — including all versions"
    )
