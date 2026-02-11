"""Session scoring and CSV generation.

Provides a unified CSV table tracking all agent sessions with their
outputs, costs, and outcomes. The CSV serves as the primary data source
for feedback loop analysis and version comparison.

Convention: columns are defined as a module-level list so that
domain-specific columns can be added by modifying CSV_COLUMNS
and build_score_row().
"""

import csv
import logging
from pathlib import Path

from loop.agent.models import SessionResult

logger = logging.getLogger(__name__)

SCORES_CSV_PATH = Path("./notes/scores.csv")

CSV_COLUMNS = [
    "session_id",
    "task_id",
    "agent_version",
    "timestamp",
    "summary",
    "confidence",
    "duration_seconds",
    "cost_usd",
    "input_tokens",
    "output_tokens",
    "outcome",
    # Add domain-specific columns here
]


def build_score_row(result: SessionResult) -> dict[str, str]:
    """Build a CSV row dict from a SessionResult.

    Customize this function to add domain-specific columns.
    """
    token_input = ""
    token_output = ""
    if result.token_usage:
        token_input = str(result.token_usage.get("input_tokens", ""))
        token_output = str(result.token_usage.get("output_tokens", ""))

    return {
        "session_id": result.session_id,
        "task_id": result.task_id or "",
        "agent_version": result.agent_version,
        "timestamp": result.timestamp,
        "summary": result.output.summary[:80],
        "confidence": f"{result.output.confidence:.4f}",
        "duration_seconds": f"{result.duration_seconds:.1f}" if result.duration_seconds else "",
        "cost_usd": f"{result.cost_usd:.4f}" if result.cost_usd else "",
        "input_tokens": token_input,
        "output_tokens": token_output,
        "outcome": result.outcome or "",
    }


def rebuild_scores_csv(results: list[SessionResult]) -> int:
    """Rebuild the scores CSV from a list of SessionResults.

    Returns the number of rows written.
    """
    rows = [build_score_row(r) for r in results]
    rows.sort(key=lambda r: (r["task_id"], r["timestamp"]))

    SCORES_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCORES_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def append_score_row(result: SessionResult) -> None:
    """Append a single score row to the CSV. Creates file with header if missing."""
    row = build_score_row(result)
    file_exists = SCORES_CSV_PATH.exists()

    SCORES_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCORES_CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def read_scores_csv() -> list[dict[str, str]]:
    """Read the scores CSV, returning empty list if missing."""
    if not SCORES_CSV_PATH.exists():
        return []
    with SCORES_CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_scores_for_task(task_id: str) -> list[dict[str, str]]:
    """Read scores for a specific task_id."""
    return [r for r in read_scores_csv() if r.get("task_id") == task_id]


def read_scores_for_version(agent_version: str) -> list[dict[str, str]]:
    """Read scores for a specific agent version."""
    return [r for r in read_scores_csv() if r.get("agent_version") == agent_version]
