"""Environment CLI for running agent sessions.

This is a TEMPLATE. Customize for your domain.

The CLI is the domain-specific harness that:
1. Handles user interaction or game logic
2. Runs agent sessions with inputs
3. Auto-commits results after each session
4. Manages application flow and lifecycle

The feedback loop focuses on improving loop.agent.
This code evolves with application requirements.

Usage:
    uv run python -m loop.environment.cli run "your task here"
    uv run python -m loop.environment.cli run --session-id my-session "task"
    uv run python -m loop.environment.cli loop "task1" "task2" "task3"
"""

import asyncio
import logging
from typing import Annotated

import sh
import typer

from loop.agent.config import settings
from loop.agent.core import run_agent
from loop.agent.models import SessionResult

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="loop",
    help="Self-improving agent CLI",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    """Self-improving agent CLI."""
    if ctx.invoked_subcommand is None:
        raise typer.Exit()


async def run_session(
    task: str,
    *,
    session_id: str | None = None,
) -> SessionResult:
    """Run an agent session with the given task.

    This is the main entry point for the environment harness.
    Customize this for your domain's needs.

    Args:
        task: The task/prompt for the agent.
        session_id: Optional session identifier.

    Returns:
        SessionResult with the agent's output and metadata.
    """
    logger.info("Starting session with model: %s", settings.model)

    result = await run_agent(
        task,
        session_id=session_id,
    )

    logger.info(
        "Session %s completed (cost: $%.4f, duration: %.1fs)",
        result.session_id,
        result.cost_usd or 0,
        result.duration_seconds or 0,
    )

    return result


def _commit_results() -> None:
    """Commit any uncommitted session results.

    TEMPLATE NOTE: This auto-commits session outputs (notes/sessions/,
    notes/traces/, notes/scores.csv) after each run. For domains like
    forecasting, game playing, or batch processing, this keeps data
    commits atomic and automatic. Customize or remove if your domain
    doesn't need auto-commit (e.g., interactive coaching).
    """
    git = sh.Command("git")
    status = str(git.status("--porcelain", "--", "notes/", _ok_code=[0])).strip()
    if not status:
        return

    try:
        git.add("notes/")
        diff = str(git.diff("--cached", "--stat", _ok_code=[0, 1])).strip()
        if diff:
            git.commit("-m", "data(sessions): auto-commit session results")
            typer.echo("Committed session results.")
    except sh.ErrorReturnCode as e:
        logger.warning("Auto-commit failed: %s", e)


def _print_result(result: SessionResult) -> None:
    """Print a session result summary."""
    typer.echo(f"\nSession: {result.session_id}")
    typer.echo(f"Output: {result.output.summary}")
    typer.echo(f"Confidence: {result.output.confidence:.1%}")
    if result.cost_usd:
        typer.echo(f"Cost: ${result.cost_usd:.4f}")
    if result.duration_seconds:
        typer.echo(f"Duration: {result.duration_seconds:.1f}s")


@app.command()
def run(
    task: Annotated[str, typer.Argument(help="The task for the agent to perform")],
    session_id: Annotated[
        str | None,
        typer.Option("--session-id", "-s", help="Optional session identifier"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
) -> None:
    """Run a single agent session."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    result = asyncio.run(run_session(task, session_id=session_id))
    _print_result(result)


@app.command()
def loop(
    tasks: Annotated[list[str], typer.Argument(help="Tasks for the agent to perform")],
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
    auto_commit: Annotated[
        bool,
        typer.Option("--commit/--no-commit", help="Auto-commit results after each task"),
    ] = True,
) -> None:
    """Run multiple agent sessions and auto-commit results.

    TEMPLATE NOTE: This is the primary entry point for batch processing.
    For a forecasting bot, tasks might be question IDs. For a game-playing
    agent, tasks might be game configs. Customize the task format and
    post-processing for your domain.

    Example:
        uv run python -m loop.environment.cli loop "task1" "task2" "task3"
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    results: list[SessionResult] = []
    total_cost = 0.0

    for i, task in enumerate(tasks, 1):
        typer.echo(f"\n{'='*60}")
        typer.echo(f"Task {i}/{len(tasks)}: {task[:80]}")
        typer.echo(f"{'='*60}")

        try:
            result = asyncio.run(run_session(task))
            results.append(result)
            total_cost += result.cost_usd or 0
            _print_result(result)
        except RuntimeError as e:
            typer.echo(f"Error: {e}", err=True)
            continue

        if auto_commit:
            _commit_results()

    typer.echo(f"\n{'='*60}")
    typer.echo(f"Completed {len(results)}/{len(tasks)} sessions")
    typer.echo(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    app()
