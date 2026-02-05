"""Environment CLI for running agent sessions.

This is a TEMPLATE. Customize for your domain.

The CLI is the domain-specific harness that:
1. Handles user interaction or game logic
2. Runs agent sessions with inputs
3. Manages application flow and lifecycle
4. Integrates with external systems

The feedback loop focuses on improving loop.agent.
This code evolves with application requirements.

Usage:
    uv run python -m loop.environment.cli run "your task here"
    uv run python -m loop.environment.cli run --session-id my-session "task"
"""

import asyncio
import logging
from typing import Annotated

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


# Use callback to handle the case of a single command while keeping subcommand explicit
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
    """Run an agent session with the given task."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    result = asyncio.run(run_session(task, session_id=session_id))

    typer.echo(f"\nSession: {result.session_id}")
    typer.echo(f"Output: {result.output.summary}")
    typer.echo(f"Confidence: {result.output.confidence:.1%}")


if __name__ == "__main__":
    app()
