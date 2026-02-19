"""Analyze reasoning traces from sessions.

This is a TEMPLATE script. Customize it for your domain's trace format.
"""

import re
from pathlib import Path

import typer

from lup.lib.paths import TRACES_PATH, iter_session_dirs, iter_trace_log_files

app = typer.Typer(no_args_is_help=True)


def _find_trace(session_id: str) -> Path | None:
    """Find the trace file for a session across all versions."""
    # Check versioned trace logs
    log_files = list(iter_trace_log_files(session_id=session_id))
    if log_files:
        return sorted(log_files)[-1]

    # Check versioned session dirs for .md files
    for session_dir in iter_session_dirs(session_id=session_id):
        md_files = list(session_dir.glob("*.md"))
        if md_files:
            return sorted(md_files)[-1]

    return None


def _load_trace(trace_path: Path) -> str:
    """Load trace content from a file or directory."""
    if trace_path.is_file():
        return trace_path.read_text(encoding="utf-8")

    if trace_path.is_dir():
        contents = []
        for f in sorted(trace_path.glob("*")):
            if f.is_file():
                contents.append(f"--- {f.name} ---\n{f.read_text(encoding='utf-8')}")
        return "\n\n".join(contents)

    return ""


@app.command("show")
def show(
    session_id: str = typer.Argument(..., help="Session ID to show trace for"),
    full: bool = typer.Option(False, "-f", "--full", help="Show full trace"),
) -> None:
    """Show trace for a session."""
    trace_path = _find_trace(session_id)

    if not trace_path:
        typer.echo(f"No trace found for session {session_id}")
        typer.echo(f"Checked: {TRACES_PATH}")
        raise typer.Exit(1)

    typer.echo(f"\n=== Trace for {session_id} ===")
    typer.echo(f"Path: {trace_path}\n")

    content = _load_trace(trace_path)

    if full:
        typer.echo(content)
    else:
        lines = content.split("\n")
        typer.echo("\n".join(lines[:100]))
        if len(lines) > 100:
            typer.echo(f"\n... ({len(lines) - 100} more lines)")
            typer.echo("Use --full to see complete trace")


@app.command("search")
def search(
    pattern: str = typer.Argument(..., help="Pattern to search for (regex)"),
    context: int = typer.Option(2, "-C", help="Lines of context around match"),
) -> None:
    """Search traces for a pattern."""
    if not TRACES_PATH.exists():
        typer.echo("No trace directories found")
        raise typer.Exit(1)

    regex = re.compile(pattern, re.IGNORECASE)
    matches_found = 0

    search_paths: list[Path] = list(TRACES_PATH.rglob("*.md"))

    for trace_file in search_paths:
        try:
            content = trace_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if regex.search(line):
                    matches_found += 1
                    typer.echo(
                        f"\n--- {trace_file.relative_to(Path.cwd())}:{i + 1} ---"
                    )

                    start = max(0, i - context)
                    end = min(len(lines), i + context + 1)
                    for j in range(start, end):
                        prefix = ">>> " if j == i else "    "
                        typer.echo(f"{prefix}{lines[j]}")

        except OSError as e:
            typer.echo(f"Error reading {trace_file}: {e}", err=True)

    typer.echo(f"\n{matches_found} matches found")


@app.command("errors")
def errors(
    limit: int = typer.Option(20, "-n", "--limit", help="Max errors to show"),
) -> None:
    """Show sessions with errors or failures."""
    error_patterns = [
        r"error",
        r"failed",
        r"exception",
        r"traceback",
        r"couldn't",
        r"unable to",
        r"not found",
        r"timeout",
    ]

    regex = re.compile("|".join(error_patterns), re.IGNORECASE)
    errors_by_session: dict[str, list[str]] = {}

    search_paths: list[Path] = list(TRACES_PATH.rglob("*.md")) if TRACES_PATH.exists() else []

    for trace_file in search_paths:
        try:
            content = trace_file.read_text(encoding="utf-8")

            parts = trace_file.relative_to(Path.cwd()).parts
            session_id = parts[1] if len(parts) > 1 else trace_file.stem

            for line in content.split("\n"):
                if regex.search(line):
                    if session_id not in errors_by_session:
                        errors_by_session[session_id] = []
                    error_line = line[:100] + "..." if len(line) > 100 else line
                    errors_by_session[session_id].append(error_line.strip())

        except OSError:
            pass

    if not errors_by_session:
        typer.echo("No errors found in traces")
        return

    typer.echo(f"\n=== Sessions with Errors ({len(errors_by_session)} total) ===\n")

    sorted_sessions = sorted(
        errors_by_session.items(), key=lambda x: len(x[1]), reverse=True
    )

    for session_id, error_lines in sorted_sessions[:limit]:
        typer.echo(f"{session_id}: {len(error_lines)} errors")
        for line in error_lines[:3]:
            typer.echo(f"  - {line}")
        if len(error_lines) > 3:
            typer.echo(f"  ... and {len(error_lines) - 3} more")
        typer.echo()


@app.command("list")
def list_traces(
    limit: int = typer.Option(20, "-n", "--limit", help="Max to show"),
) -> None:
    """List available traces."""
    traces: list[tuple[str, str, Path]] = []

    # Collect trace logs across all versions
    for session_dir in iter_session_dirs():
        traces.append(("sessions", session_dir.name, session_dir))

    for log_file in iter_trace_log_files():
        session_id = log_file.parent.name
        traces.append(("logs", session_id, log_file.parent))

    if not traces:
        typer.echo("No traces found")
        typer.echo(f"Checked: {TRACES_PATH}")
        return

    # Deduplicate by session_id, preferring logs
    seen: dict[str, tuple[str, str, Path]] = {}
    for source, session_id, path in traces:
        if session_id not in seen or source == "logs":
            seen[session_id] = (source, session_id, path)

    unique = list(seen.values())
    typer.echo(f"\n=== Available Traces ({len(unique)} total) ===\n")

    for source, session_id, path in sorted(unique, reverse=True)[:limit]:
        files = list(path.glob("*"))
        size = sum(f.stat().st_size for f in files if f.is_file())
        size_kb = size / 1024

        typer.echo(f"{session_id} ({source}): {len(files)} files, {size_kb:.1f}KB")


@app.command("capabilities")
def capabilities() -> None:
    """Extract capability requests from traces."""
    capability_patterns = [
        r"would be useful",
        r"would have helped",
        r"would benefit from",
        r"wish I had",
        r"if I could",
        r"tool that",
        r"need.* access to",
        r"cannot .* because",
    ]

    regex = re.compile("|".join(capability_patterns), re.IGNORECASE)
    requests: list[tuple[str, str]] = []

    search_paths: list[Path] = list(TRACES_PATH.rglob("*.md")) if TRACES_PATH.exists() else []

    for trace_file in search_paths:
        try:
            content = trace_file.read_text(encoding="utf-8")

            for line in content.split("\n"):
                if regex.search(line):
                    requests.append((str(trace_file), line.strip()))

        except OSError:
            pass

    if not requests:
        typer.echo("No capability requests found in traces")
        return

    typer.echo(f"\n=== Capability Requests ({len(requests)} found) ===\n")

    for _file_path, request in requests[:30]:
        request_short = request[:80] + "..." if len(request) > 80 else request
        typer.echo(f"- {request_short}")
