"""Analyze reasoning traces from sessions.

This is a TEMPLATE script. Customize it for your domain's trace format.
"""

import re
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)

TRACES_PATH = Path("./notes/traces")
SESSIONS_PATH = Path("./notes/sessions")


def _find_trace(session_id: str) -> Path | None:
    """Find the trace file for a session."""
    candidates = [
        TRACES_PATH / session_id / "trace.md",
        TRACES_PATH / f"{session_id}.md",
        SESSIONS_PATH / session_id / "reasoning.md",
        Path("logs") / session_id,
    ]

    for path in candidates:
        if path.exists():
            return path

    session_dir = SESSIONS_PATH / session_id
    if session_dir.exists():
        md_files = list(session_dir.glob("*.md"))
        if md_files:
            return md_files[0]

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
        typer.echo(f"Checked: {TRACES_PATH}, {SESSIONS_PATH}")
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
    if not TRACES_PATH.exists() and not SESSIONS_PATH.exists():
        typer.echo("No trace directories found")
        raise typer.Exit(1)

    regex = re.compile(pattern, re.IGNORECASE)
    matches_found = 0

    search_paths: list[Path] = []
    if TRACES_PATH.exists():
        search_paths.extend(TRACES_PATH.rglob("*.md"))
    if SESSIONS_PATH.exists():
        search_paths.extend(SESSIONS_PATH.rglob("*.md"))

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

    search_paths: list[Path] = []
    if TRACES_PATH.exists():
        search_paths.extend(TRACES_PATH.rglob("*.md"))
    if SESSIONS_PATH.exists():
        search_paths.extend(SESSIONS_PATH.rglob("*.md"))

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

    if TRACES_PATH.exists():
        for d in TRACES_PATH.iterdir():
            if d.is_dir():
                traces.append(("traces", d.name, d))
    if SESSIONS_PATH.exists():
        for d in SESSIONS_PATH.iterdir():
            if d.is_dir() and list(d.glob("*.md")):
                traces.append(("sessions", d.name, d))

    if not traces:
        typer.echo("No traces found")
        typer.echo(f"Checked: {TRACES_PATH}, {SESSIONS_PATH}")
        return

    typer.echo(f"\n=== Available Traces ({len(traces)} total) ===\n")

    for source, session_id, path in sorted(traces, reverse=True)[:limit]:
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

    search_paths: list[Path] = []
    if TRACES_PATH.exists():
        search_paths.extend(TRACES_PATH.rglob("*.md"))
    if SESSIONS_PATH.exists():
        search_paths.extend(SESSIONS_PATH.rglob("*.md"))

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
