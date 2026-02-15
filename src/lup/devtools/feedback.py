"""Collect feedback data from agent sessions.

This is a TEMPLATE script. Run `/lup:init` to customize it for your domain.

The script should:
1. Load session data from notes/sessions/
2. Match sessions to their outcomes/feedback
3. Compute aggregate metrics
4. Save results to notes/feedback_loop/
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel

app = typer.Typer(no_args_is_help=True)
logger = logging.getLogger(__name__)

SESSIONS_PATH = Path("./notes/sessions")
FEEDBACK_PATH = Path("./notes/feedback_loop")
TRACES_PATH = Path("./notes/traces")


# =============================================================================
# CUSTOMIZE THESE MODELS FOR YOUR DOMAIN
# =============================================================================


class SessionResult(BaseModel):
    """A session matched with its outcome/feedback.

    Customize this for your domain. Examples:

    For forecasting:
        question_id: int
        probability: float
        resolution: bool | None
        brier_score: float | None

    For coaching:
        conversation_id: str
        user_rating: int | None
        session_duration: float
        goals_addressed: list[str]

    For game playing:
        game_id: str
        outcome: str  # "win", "loss", "draw"
        moves_played: int
        opponent_strength: float
    """

    session_id: str
    timestamp: str
    outcome: Any | None = None
    metrics: dict[str, Any] | None = None


class FeedbackMetrics(BaseModel):
    """Aggregated metrics from sessions.

    Customize this for your domain.
    """

    collection_timestamp: str
    since_timestamp: str | None = None
    total_sessions: int
    sessions_with_outcomes: int
    results: list[SessionResult] = []


# =============================================================================
# CUSTOMIZE THESE FUNCTIONS FOR YOUR DOMAIN
# =============================================================================


def load_sessions(since: datetime | None = None) -> list[dict[str, Any]]:
    """Load all session data."""
    sessions: list[dict[str, Any]] = []
    if not SESSIONS_PATH.exists():
        return sessions

    for session_dir in SESSIONS_PATH.iterdir():
        if not session_dir.is_dir():
            continue

        session_files = sorted(session_dir.glob("*.json"), reverse=True)
        if not session_files:
            continue

        try:
            data: dict[str, Any] = json.loads(session_files[0].read_text())
            data["_session_id"] = session_dir.name
            data["_file"] = str(session_files[0])

            if since and data.get("timestamp"):
                session_time = datetime.fromisoformat(data["timestamp"])
                if session_time < since:
                    continue

            sessions.append(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load session %s: %s", session_dir.name, e)

    return sessions


def load_outcomes() -> dict[str, Any]:
    """Load outcome data for sessions.

    Customize this to load outcomes for your domain.
    """
    return {}


def match_outcomes(sessions: list[dict[str, Any]]) -> list[SessionResult]:
    """Match sessions to their outcomes/feedback."""
    outcomes = load_outcomes()
    results = []

    for session in sessions:
        session_id = session.get("_session_id", "")
        timestamp = session.get("timestamp", "")

        outcome_data = outcomes.get(session_id)

        result = SessionResult(
            session_id=session_id,
            timestamp=timestamp,
            outcome=outcome_data,
            metrics=session.get("tool_metrics"),
        )
        results.append(result)

    return results


def compute_metrics(results: list[SessionResult]) -> FeedbackMetrics:
    """Compute aggregate metrics from session results."""
    sessions_with_outcomes = sum(1 for r in results if r.outcome is not None)

    return FeedbackMetrics(
        collection_timestamp=datetime.now().isoformat(),
        total_sessions=len(results),
        sessions_with_outcomes=sessions_with_outcomes,
        results=results,
    )


# =============================================================================
# CLI COMMANDS
# =============================================================================


@app.command("collect")
def collect(
    since: Annotated[
        str | None,
        typer.Option(
            "--since", "-s", help="Only sessions after this date (YYYY-MM-DD)"
        ),
    ] = None,
    all_time: Annotated[
        bool,
        typer.Option("--all-time", help="Include all sessions regardless of date"),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
) -> None:
    """Collect feedback metrics from sessions."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    since_dt: datetime | None = None
    if not all_time and since:
        since_dt = datetime.fromisoformat(since)

    logger.info(
        "Collecting feedback since %s",
        since_dt.isoformat() if since_dt else "all time",
    )

    sessions = load_sessions(since_dt)
    logger.info("Found %d sessions", len(sessions))

    results = match_outcomes(sessions)
    metrics = compute_metrics(results)

    if output is None:
        FEEDBACK_PATH.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = FEEDBACK_PATH / f"{timestamp}_metrics.json"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(metrics.model_dump_json(indent=2))
    logger.info("Saved metrics to %s", output)

    print("\n" + "=" * 60)
    print("FEEDBACK COLLECTION SUMMARY")
    print("=" * 60)
    print(f"Total sessions: {metrics.total_sessions}")
    print(f"Sessions with outcomes: {metrics.sessions_with_outcomes}")
    print(f"\nMetrics saved to: {output}")


@app.command("check")
def check() -> None:
    """Check what data is available for feedback collection."""
    print("\n=== Feedback Data Check ===\n")

    if SESSIONS_PATH.exists():
        session_count = sum(1 for d in SESSIONS_PATH.iterdir() if d.is_dir())
        print(f"Sessions: {session_count} in {SESSIONS_PATH}")
    else:
        print(f"Sessions: No directory at {SESSIONS_PATH}")

    if TRACES_PATH.exists():
        trace_count = sum(1 for d in TRACES_PATH.iterdir() if d.is_dir())
        print(f"Traces: {trace_count} in {TRACES_PATH}")
    else:
        print(f"Traces: No directory at {TRACES_PATH}")

    if FEEDBACK_PATH.exists():
        feedback_files = list(FEEDBACK_PATH.glob("*_metrics.json"))
        print(f"Previous feedback collections: {len(feedback_files)}")
        if feedback_files:
            latest = sorted(feedback_files)[-1]
            print(f"  Latest: {latest.name}")
    else:
        print("Previous feedback collections: None")

    print("\nTo collect feedback, run:")
    print("  uv run lup-devtools feedback collect")
