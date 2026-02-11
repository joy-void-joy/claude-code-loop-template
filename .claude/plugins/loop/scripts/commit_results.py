"""Commit uncommitted session result files to git.

Finds all modified/untracked files under notes/sessions/ and notes/traces/,
groups them by session ID, and creates one commit per session.
"""

import json
from pathlib import Path

import sh
import typer

app = typer.Typer()

SESSIONS_PATH = Path("./notes/sessions")
TRACES_PATH = Path("./notes/traces")
SCORES_CSV = Path("./notes/scores.csv")


def _get_uncommitted_session_ids() -> set[str]:
    """Find session IDs with uncommitted result files."""
    git = sh.Command("git")
    session_ids: set[str] = set()

    status = str(git.status("--porcelain", "--", "notes/", _ok_code=[0])).strip()
    if not status:
        return session_ids

    for line in status.splitlines():
        file_path = line[3:].split(" -> ")[0].strip()
        parts = Path(file_path).parts

        # notes/sessions/<session_id>/... or notes/traces/<session_id>/...
        if (
            len(parts) >= 3
            and parts[0] == "notes"
            and parts[1] in ("sessions", "traces")
        ):
            session_ids.add(parts[2])

    return session_ids


def _get_session_summary(session_id: str) -> str:
    """Read summary from the latest session JSON."""
    session_dir = SESSIONS_PATH / session_id
    if not session_dir.exists():
        return f"session {session_id}"

    json_files = sorted(session_dir.glob("*.json"))
    if not json_files:
        return f"session {session_id}"

    try:
        data = json.loads(json_files[-1].read_text(encoding="utf-8"))
        output = data.get("output", {})
        if isinstance(output, dict):
            return output.get("summary", f"session {session_id}")[:50]
        return f"session {session_id}"
    except (json.JSONDecodeError, OSError):
        return f"session {session_id}"


def _commit_session(session_id: str, *, dry_run: bool = False) -> bool:
    """Stage and commit files for a single session ID."""
    git = sh.Command("git")
    paths: list[str] = []

    session_dir = SESSIONS_PATH / session_id
    if session_dir.exists():
        paths.append(str(session_dir))

    trace_dir = TRACES_PATH / session_id
    if trace_dir.exists():
        paths.append(str(trace_dir))

    if not paths:
        return False

    if dry_run:
        summary = _get_session_summary(session_id)
        print(f"  Would commit {session_id}: {summary}")
        for p in paths:
            print(f"    {p}")
        return True

    for path in paths:
        try:
            git.add(path)
        except sh.ErrorReturnCode:
            pass

    # Also stage scores.csv if it has changes
    if SCORES_CSV.exists():
        try:
            git.add(str(SCORES_CSV))
        except sh.ErrorReturnCode:
            pass

    diff = str(git.diff("--cached", "--stat", _ok_code=[0, 1])).strip()
    if not diff:
        return False

    summary = _get_session_summary(session_id)
    slug = summary[:50].strip().rstrip(".")
    git.commit("-m", f"data(sessions): {slug}")
    print(f"  Committed {session_id}: {slug}")
    return True


@app.command()
def main(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be committed"
    ),
) -> None:
    """Commit all uncommitted session result files, one commit per session."""
    session_ids = _get_uncommitted_session_ids()

    if not session_ids:
        print("Nothing to commit.")
        return

    print(f"Found {len(session_ids)} session(s) with uncommitted files")

    committed = 0
    for session_id in sorted(session_ids):
        try:
            if _commit_session(session_id, dry_run=dry_run):
                committed += 1
        except sh.ErrorReturnCode as e:
            print(f"  Failed {session_id}: {e}")

    if dry_run:
        print(f"\nWould commit {committed} session(s)")
    else:
        print(f"\nCommitted {committed} session(s)")


if __name__ == "__main__":
    app()
