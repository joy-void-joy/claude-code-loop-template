"""Git operations for session data.

Examples::

    $ uv run lup-devtools git commit-results
    $ uv run lup-devtools git commit-results --dry-run
"""

import json
import logging
from pathlib import Path

import sh
import typer

from lup.lib.paths import iter_session_dirs, traces_path

logger = logging.getLogger(__name__)
app = typer.Typer(no_args_is_help=True)


def get_uncommitted_session_ids() -> set[str]:
    """Find session IDs with uncommitted result files.

    Parses git status for paths like:
        notes/traces/<version>/sessions/<session_id>/...
        notes/traces/<version>/logs/<session_id>/...
    """
    git = sh.Command("git")
    session_ids: set[str] = set()

    status = str(git.status("--porcelain", "--", "notes/", _ok_code=[0])).strip()
    if not status:
        return session_ids

    for line in status.splitlines():
        file_path = line[3:].split(" -> ")[0].strip()
        parts = Path(file_path).parts

        # notes/traces/<version>/sessions/<session_id>/...
        # notes/traces/<version>/logs/<session_id>/...
        if (
            len(parts) >= 5
            and parts[0] == "notes"
            and parts[1] == "traces"
            and parts[3] in ("sessions", "logs")
        ):
            session_ids.add(parts[4])

    return session_ids


def get_session_summary(session_id: str) -> str:
    """Read summary from the latest session JSON across all versions."""
    all_json: list[Path] = []
    for session_dir in iter_session_dirs(session_id=session_id):
        all_json.extend(session_dir.glob("*.json"))

    if not all_json:
        return f"session {session_id}"

    latest = sorted(all_json)[-1]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        output = data.get("output", {})
        if isinstance(output, dict):
            return output.get("summary", f"session {session_id}")[:50]
        return f"session {session_id}"
    except (json.JSONDecodeError, OSError):
        return f"session {session_id}"


def commit_session(session_id: str, *, dry_run: bool = False) -> bool:
    """Stage and commit files for a single session ID."""
    git = sh.Command("git")
    paths: list[str] = []

    # Find session and log dirs across all versions
    for session_dir in iter_session_dirs(session_id=session_id):
        paths.append(str(session_dir))

    # Also check for trace log dirs under each version
    if traces_path().exists():
        for ver_dir in traces_path().iterdir():
            if not ver_dir.is_dir():
                continue
            log_dir = ver_dir / "logs" / session_id
            if log_dir.exists():
                paths.append(str(log_dir))

    if not paths:
        return False

    if dry_run:
        summary = get_session_summary(session_id)
        print(f"  Would commit {session_id}: {summary}")
        for p in paths:
            print(f"    {p}")
        return True

    for path in paths:
        try:
            git.add(path)
        except sh.ErrorReturnCode as e:
            logger.warning("Failed to stage %s: %s", path, e)

    diff = str(git.diff("--cached", "--stat", _ok_code=[0, 1])).strip()
    if not diff:
        return False

    summary = get_session_summary(session_id)
    slug = summary[:50].strip().rstrip(".")
    git.commit("-m", f"data(sessions): {slug}")
    print(f"  Committed {session_id}: {slug}")
    return True


@app.command("commit-results")
def commit_results(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be committed"
    ),
) -> None:
    """Commit all uncommitted session result files, one commit per session."""
    session_ids = get_uncommitted_session_ids()

    if not session_ids:
        print("Nothing to commit.")
        return

    print(f"Found {len(session_ids)} session(s) with uncommitted files")

    committed = 0
    for session_id in sorted(session_ids):
        try:
            if commit_session(session_id, dry_run=dry_run):
                committed += 1
        except sh.ErrorReturnCode as e:
            print(f"  Failed {session_id}: {e}")

    if dry_run:
        print(f"\nWould commit {committed} session(s)")
    else:
        print(f"\nCommitted {committed} session(s)")
