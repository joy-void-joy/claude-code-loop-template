"""Aggregate metrics across all sessions.

This is a TEMPLATE script. Customize it for your domain's metrics.
"""

import json
from collections import defaultdict
from typing import Any

import typer

from lup.lib.paths import FEEDBACK_PATH, iter_session_dirs

app = typer.Typer(no_args_is_help=True)


def _load_all_sessions() -> list[dict[str, Any]]:
    """Load all session files across all versions."""
    sessions: list[dict[str, Any]] = []

    for session_dir in iter_session_dirs():
        for session_file in session_dir.glob("*.json"):
            try:
                data: dict[str, Any] = json.loads(session_file.read_text())
                data["_file"] = str(session_file)
                data["_session_id"] = session_dir.name
                sessions.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    return sessions


@app.command("summary")
def summary() -> None:
    """Show aggregate summary of all sessions."""
    sessions = _load_all_sessions()
    if not sessions:
        typer.echo("No sessions found")
        typer.echo("Checked all version directories under notes/traces/")
        raise typer.Exit(1)

    total = len(sessions)
    with_metrics = sum(1 for s in sessions if s.get("tool_metrics"))
    with_tokens = sum(1 for s in sessions if s.get("token_usage"))
    with_outcome = sum(1 for s in sessions if s.get("outcome") is not None)

    typer.echo(f"\n=== Session Summary ({total} total) ===\n")
    typer.echo(f"With metrics: {with_metrics} ({100 * with_metrics / total:.0f}%)")
    typer.echo(f"With tokens:  {with_tokens} ({100 * with_tokens / total:.0f}%)")
    typer.echo(f"With outcome: {with_outcome} ({100 * with_outcome / total:.0f}%)")

    total_cost = 0.0
    for s in sessions:
        cost = s.get("cost_usd") or s.get("tool_metrics", {}).get("total_cost_usd", 0)
        if cost:
            total_cost += cost

    if total_cost > 0:
        typer.echo(f"\nTotal cost: ${total_cost:.2f}")
        typer.echo(f"Avg cost/session: ${total_cost / total:.4f}")

    total_input = 0
    total_output = 0
    for s in sessions:
        usage = s.get("token_usage", {})
        if usage:
            total_input += usage.get("input_tokens", 0) or 0
            total_output += usage.get("output_tokens", 0) or 0

    if total_input or total_output:
        typer.echo("\nTokens:")
        typer.echo(f"  Input:  {total_input:,}")
        typer.echo(f"  Output: {total_output:,}")
        typer.echo(f"  Total:  {total_input + total_output:,}")


@app.command("tools")
def tools() -> None:
    """Show tool usage aggregates."""
    sessions = _load_all_sessions()
    if not sessions:
        typer.echo("No sessions found")
        raise typer.Exit(1)

    tool_stats: dict[str, dict[str, int | float]] = defaultdict(
        lambda: {"calls": 0, "errors": 0, "total_ms": 0}
    )

    for s in sessions:
        metrics = s.get("tool_metrics", {})
        by_tool = metrics.get("by_tool", {})
        for tool_name, data in by_tool.items():
            tool_stats[tool_name]["calls"] += data.get("call_count", 0)
            tool_stats[tool_name]["errors"] += data.get("error_count", 0)
            avg_ms = data.get("avg_duration_ms", 0)
            count = data.get("call_count", 0)
            tool_stats[tool_name]["total_ms"] += avg_ms * count

    if not tool_stats:
        typer.echo("No tool metrics found")
        return

    typer.echo("\n=== Tool Usage Summary ===\n")
    typer.echo(f"{'Tool':<35} {'Calls':>8} {'Errors':>8} {'Err%':>8} {'Avg ms':>10}")
    typer.echo("-" * 75)

    for tool_name in sorted(tool_stats.keys(), key=lambda t: -tool_stats[t]["calls"]):
        stats = tool_stats[tool_name]
        calls = int(stats["calls"])
        errs = int(stats["errors"])
        err_pct = (100 * errs / calls) if calls > 0 else 0
        avg_ms = stats["total_ms"] / calls if calls > 0 else 0
        err_indicator = " !" if err_pct > 10 else ""
        typer.echo(
            f"{tool_name:<35} {calls:>8} {errs:>8} {err_pct:>7.1f}%{err_indicator} {avg_ms:>9.0f}"
        )


@app.command("errors")
def errors(
    limit: int = typer.Option(20, "-n", "--limit", help="Max sessions to show"),
) -> None:
    """Show sessions with high error rates."""
    sessions = _load_all_sessions()
    if not sessions:
        typer.echo("No sessions found")
        raise typer.Exit(1)

    with_errors: list[dict[str, Any]] = []
    for s in sessions:
        metrics = s.get("tool_metrics", {})
        total_errors = metrics.get("total_errors", 0)
        if total_errors and total_errors > 0:
            with_errors.append(
                {
                    "session_id": s.get("_session_id"),
                    "errors": total_errors,
                    "by_tool": metrics.get("by_tool", {}),
                }
            )

    if not with_errors:
        typer.echo("No sessions with errors found")
        return

    with_errors.sort(key=lambda x: -x["errors"])

    typer.echo(f"\n=== Sessions with Errors ({len(with_errors)} total) ===\n")

    for item in with_errors[:limit]:
        typer.echo(f"Session {item['session_id']}: {item['errors']} errors")
        for tool_name, tool_data in item["by_tool"].items():
            errs = tool_data.get("error_count", 0)
            if errs > 0:
                typer.echo(f"  - {tool_name}: {errs}")


@app.command("trends")
def trends(
    window: int = typer.Option(10, "-w", "--window", help="Rolling window size"),
) -> None:
    """Show metric trends over time."""
    sessions = _load_all_sessions()
    if not sessions:
        typer.echo("No sessions found")
        raise typer.Exit(1)

    sessions_with_ts = [s for s in sessions if s.get("timestamp")]
    sessions_with_ts.sort(key=lambda x: x["timestamp"])

    if len(sessions_with_ts) < window:
        typer.echo(f"Need at least {window} sessions for trend analysis")
        typer.echo(f"Have: {len(sessions_with_ts)}")
        return

    typer.echo(f"\n=== Trends (rolling {window}-session window) ===\n")

    for i in range(window - 1, len(sessions_with_ts)):
        window_sessions = sessions_with_ts[i - window + 1 : i + 1]

        total_calls = sum(
            s.get("tool_metrics", {}).get("total_tool_calls", 0)
            for s in window_sessions
        )
        avg_calls = total_calls / window

        total_errors = sum(
            s.get("tool_metrics", {}).get("total_errors", 0) for s in window_sessions
        )
        error_rate = total_errors / max(1, total_calls)

        total_cost = sum(s.get("cost_usd", 0) or 0 for s in window_sessions)
        avg_cost = total_cost / window

        latest_ts = window_sessions[-1].get("timestamp", "")[:10]
        typer.echo(
            f"{latest_ts}: calls={avg_calls:.1f}/session, "
            f"errors={error_rate:.1%}, cost=${avg_cost:.4f}/session"
        )


@app.command("history")
def history(
    limit: int = typer.Option(10, "-n", "--limit", help="Max to show"),
) -> None:
    """Show previous feedback collection runs."""
    if not FEEDBACK_PATH.exists():
        typer.echo("No feedback history found")
        return

    metrics_files = sorted(FEEDBACK_PATH.glob("*_metrics.json"), reverse=True)
    if not metrics_files:
        typer.echo("No metrics files found")
        return

    typer.echo("\n=== Feedback Collection History ===\n")

    for f in metrics_files[:limit]:
        try:
            data = json.loads(f.read_text())
            total = data.get("total_sessions", 0)
            with_outcomes = data.get("sessions_with_outcomes", 0)
            typer.echo(f"{f.name}: {total} sessions, {with_outcomes} with outcomes")
        except (json.JSONDecodeError, OSError):
            typer.echo(f"{f.name}: (error reading)")
