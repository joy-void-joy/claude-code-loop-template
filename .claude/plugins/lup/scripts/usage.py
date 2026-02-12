#!/usr/bin/env python3
"""Display Claude Code usage from the live API.

Calls the /api/oauth/usage endpoint for real-time utilization data
and supplements with stats-cache.json for daily detail.

Usage:
    uv run python .claude/plugins/lup/scripts/usage.py
    uv run python .claude/plugins/lup/scripts/usage.py --no-detail
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(help="Claude Code live usage display")
console = Console()

CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
STATS_PATH = Path.home() / ".claude" / "stats-cache.json"

USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
ANTHROPIC_BETA = "oauth-2025-04-20"

MODEL_NAMES: dict[str, str] = {
    "claude-opus-4-6": "Opus 4.6",
    "claude-opus-4-5-20251101": "Opus 4.5",
    "claude-sonnet-4-5-20250929": "Sonnet 4.5",
    "claude-sonnet-4-20250514": "Sonnet 4",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
}

MODEL_COLORS: dict[str, str] = {
    "opus": "bright_magenta",
    "sonnet": "bright_blue",
    "haiku": "bright_cyan",
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_COLORS = [
    "bright_red",
    "bright_yellow",
    "bright_green",
    "bright_cyan",
    "bright_blue",
    "bright_magenta",
    "white",
]


# ── types ────────────────────────────────────────────────

from typing import TypedDict


class UsageBucket(TypedDict):
    utilization: float
    resets_at: str


class ExtraUsage(TypedDict):
    is_enabled: bool
    monthly_limit: int
    used_credits: float
    utilization: float


class UsageResponse(TypedDict):
    five_hour: UsageBucket | None
    seven_day: UsageBucket | None
    seven_day_opus: UsageBucket | None
    seven_day_sonnet: UsageBucket | None
    seven_day_oauth_apps: UsageBucket | None
    seven_day_cowork: UsageBucket | None
    iguana_necktie: UsageBucket | None
    extra_usage: ExtraUsage | None


# ── API ──────────────────────────────────────────────────


def fetch_usage() -> UsageResponse:
    """Call the live usage API."""
    creds = json.loads(CREDS_PATH.read_text())
    oauth = creds["claudeAiOauth"]
    token = oauth["accessToken"]

    resp = httpx.get(
        USAGE_API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": ANTHROPIC_BETA,
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


# ── stats cache (supplementary detail) ───────────────────


def load_stats() -> dict[str, object] | None:
    if not STATS_PATH.exists():
        return None
    try:
        return json.loads(STATS_PATH.read_text())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return None


def get_daily_breakdown(
    stats: dict[str, object],
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[str, int, dict[str, int], int]]:
    """Get (date_iso, total_tokens, tokens_by_model, messages) per day."""
    daily_tokens: dict[str, dict[str, int]] = {}
    for entry in stats.get("dailyModelTokens", []):  # type: ignore[union-attr]
        daily_tokens[entry["date"]] = entry.get("tokensByModel", {})

    daily_activity: dict[str, dict[str, int]] = {}
    for entry in stats.get("dailyActivity", []):  # type: ignore[union-attr]
        daily_activity[entry["date"]] = entry

    days: list[tuple[str, int, dict[str, int], int]] = []
    d = window_start.date()
    end = window_end.date()
    while d <= end:
        ds = d.isoformat()
        by_model = daily_tokens.get(ds, {})
        total = sum(by_model.values())
        msgs = daily_activity.get(ds, {}).get("messageCount", 0)
        days.append((ds, total, by_model, msgs))
        d += timedelta(days=1)
    return days


# ── formatting helpers ───────────────────────────────────


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def fmt_countdown(dt: datetime) -> str:
    remaining = dt - datetime.now(dt.tzinfo)
    total_seconds = remaining.total_seconds()
    if total_seconds <= 0:
        return "now"
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    if h >= 48:
        return f"{h // 24}d {h % 24}h"
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def model_color(model_id: str) -> str:
    for key, color in MODEL_COLORS.items():
        if key in model_id:
            return color
    return "white"


def pace_color(ratio: float) -> str:
    if ratio <= 0.7:
        return "bright_green"
    if ratio <= 1.0:
        return "bright_cyan"
    if ratio <= 1.3:
        return "bright_yellow"
    return "bright_red"


def pace_word(ratio: float) -> tuple[str, str]:
    if ratio <= 0.5:
        return "cruising", "bold bright_green"
    if ratio <= 0.85:
        return "on track", "bold bright_cyan"
    if ratio <= 1.0:
        return "on pace", "bold bright_cyan"
    if ratio <= 1.3:
        return "ahead", "bold bright_yellow"
    if ratio <= 1.6:
        return "running hot", "bold bright_red"
    return "heavy usage", "bold red"


# ── bar rendering ────────────────────────────────────────


def render_bar(
    out: Text,
    utilization: float,
    linear_pct: float,
    bar_width: int,
) -> None:
    """Render a pacing bar with actual fill and a linear-pace marker."""
    actual_frac = utilization / 100.0
    linear_frac = linear_pct / 100.0
    fill_color = pace_color(actual_frac / linear_frac if linear_frac > 0 else 0)

    actual_pos = min(int(actual_frac * bar_width), bar_width)
    linear_pos = min(int(linear_frac * bar_width), bar_width - 1)

    out.append("  ")
    for i in range(bar_width):
        if i == linear_pos:
            if i < actual_pos:
                out.append("▎", style="bold white on " + fill_color)
            else:
                out.append("▎", style="bold bright_white")
        elif i < actual_pos:
            out.append("█", style=fill_color)
        else:
            out.append("░", style="bright_black")
    out.append("\n")


def render_bucket(
    out: Text,
    label: str,
    bucket: UsageBucket,
    window_hours: float,
    bar_width: int,
) -> None:
    """Render a usage bucket: label, pacing bar, annotations."""
    utilization = bucket["utilization"]
    resets_at = datetime.fromisoformat(bucket["resets_at"])
    window_start = resets_at - timedelta(hours=window_hours)
    now = datetime.now(resets_at.tzinfo)

    elapsed = (now - window_start).total_seconds()
    total = window_hours * 3600
    linear_pct = min((elapsed / total) * 100, 100) if total > 0 else 0
    ratio = (utilization / linear_pct) if linear_pct > 0 else 0

    word, word_style = pace_word(ratio)

    out.append(f"  {label}", style="bold bright_white")
    out.append(f"  {utilization:.0f}%", style="bold")
    out.append(f"  ◆ {word}", style=word_style)
    out.append(f"  resets in {fmt_countdown(resets_at)}", style="dim")
    out.append("\n")

    render_bar(out, utilization, linear_pct, bar_width)

    # Annotation lines (one per marker)
    you_label = f"↑ you ({utilization:.0f}%)"
    pace_label = f"↑ even ({linear_pct:.0f}%)"

    you_line = [" "] * (bar_width + 2)
    actual_pos = min(int((utilization / 100) * bar_width), bar_width - len(you_label))
    for j, ch in enumerate(you_label):
        pos = actual_pos + j
        if 0 <= pos < len(you_line):
            you_line[pos] = ch
    out.append("".join(you_line), style="dim")
    out.append("\n")

    pace_line = [" "] * (bar_width + 2)
    linear_pos = min(int((linear_pct / 100) * bar_width), len(pace_line) - len(pace_label))
    for j, ch in enumerate(pace_label):
        pos = linear_pos + j
        if 0 <= pos < len(pace_line):
            pace_line[pos] = ch
    out.append("".join(pace_line), style="dim")
    out.append("\n")


# ── main display ─────────────────────────────────────────


def build_display(
    usage: UsageResponse,
    stats: dict[str, object] | None,
    show_detail: bool,
    bar_width: int,
) -> Panel:
    out = Text()

    # ── 7-day usage (headline) ──
    seven_day = usage.get("seven_day")
    if seven_day:
        render_bucket(out, "weekly", seven_day, 7 * 24, bar_width)
        out.append("\n")

    # ── 5-hour rolling ──
    five_hour = usage.get("five_hour")
    if five_hour:
        render_bucket(out, "5-hour", five_hour, 5, bar_width)
        out.append("\n")

    # ── per-model buckets ──
    for key, label in [
        ("seven_day_opus", "opus 7d"),
        ("seven_day_sonnet", "sonnet 7d"),
        ("seven_day_cowork", "cowork 7d"),
        ("seven_day_oauth_apps", "oauth 7d"),
    ]:
        bucket = usage.get(key)  # type: ignore[literal-required]
        if bucket:
            render_bucket(out, label, bucket, 7 * 24, bar_width)
            out.append("\n")

    # ── extra usage (overage) ──
    extra = usage.get("extra_usage")
    if extra and extra["is_enabled"]:
        used = extra["used_credits"]
        limit = extra["monthly_limit"]
        util = extra["utilization"]
        out.append("  overage", style="bold bright_white")
        out.append(f"  ${used / 100:.2f}", style="bold")
        out.append(f" / ${limit / 100:.2f}", style="dim")
        out.append(f"  ({util:.0f}%)", style="bold")
        out.append("\n")

        fill_color = "bright_green" if util < 50 else "bright_yellow" if util < 80 else "bright_red"
        filled = min(int((util / 100) * bar_width), bar_width)
        out.append("  ")
        for i in range(bar_width):
            if i < filled:
                out.append("█", style=fill_color)
            else:
                out.append("░", style="bright_black")
        out.append("\n\n")

    # ── daily breakdown (from cache) ──
    if show_detail and stats and seven_day:
        resets_at = datetime.fromisoformat(seven_day["resets_at"])
        window_start = resets_at - timedelta(days=7)
        today = datetime.now(resets_at.tzinfo).date()

        daily = get_daily_breakdown(stats, window_start, resets_at)
        if any(d[1] > 0 for d in daily):
            out.append("  per day", style="bold bright_white")

            last_computed = str(stats.get("lastComputedDate", ""))
            if last_computed and last_computed < today.isoformat():
                out.append(f"  (cache: {last_computed})", style="dim italic")
            out.append("\n")

            max_day = max((d[1] for d in daily), default=1) or 1
            day_bar_w = bar_width - 14

            for i, (ds, total, _, msgs) in enumerate(daily):
                d = datetime.fromisoformat(ds).date()
                day_name = DAY_NAMES[d.weekday()]
                color_idx = i % len(DAY_COLORS)

                if d == today:
                    out.append(f"  {day_name}", style="bold bright_white")
                    out.append(" ←  ", style="bold bright_cyan")
                elif d > today:
                    out.append(f"  {day_name}    ", style="dim")
                else:
                    out.append(f"  {day_name}    ", style="")

                if d > today:
                    out.append("·" * day_bar_w, style="bright_black")
                    out.append("\n")
                else:
                    filled = max(1, int((total / max_day) * day_bar_w)) if total > 0 else 0
                    out.append("█" * filled, style=DAY_COLORS[color_idx])
                    out.append("░" * (day_bar_w - filled), style="bright_black")
                    out.append(f" {fmt_tokens(total):>5}", style="bold")
                    if msgs > 0:
                        out.append(f"  {msgs:,}m", style="dim")
                    out.append("\n")

            out.append("\n")

            # model breakdown
            totals: dict[str, int] = {}
            week_total = 0
            for _, total, by_model, _ in daily:
                week_total += total
                for model, tokens in by_model.items():
                    totals[model] = totals.get(model, 0) + tokens

            if totals:
                out.append("  models", style="bold bright_white")
                out.append("  ")
                for model, tokens in sorted(totals.items(), key=lambda x: x[1], reverse=True):
                    name = MODEL_NAMES.get(model, model)
                    pct = tokens / week_total * 100 if week_total > 0 else 0
                    out.append(f"● {name} ", style=model_color(model))
                    out.append(f"{pct:.0f}%  ", style="dim")
                out.append("\n")

    return Panel(
        out,
        title="[bold bright_white]Claude Code Usage[/bold bright_white]",
        border_style="bright_cyan",
        padding=(1, 1),
    )


@app.command()
def main(
    detail: Annotated[
        bool,
        typer.Option(
            "--detail/--no-detail",
            help="Show daily breakdown from stats cache.",
        ),
    ] = True,
) -> None:
    """Show live Claude Code usage with pacing bars."""
    if not CREDS_PATH.exists():
        console.print("[red]No credentials at ~/.claude/.credentials.json[/red]")
        raise typer.Exit(1)

    try:
        usage = fetch_usage()
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API error: {e.response.status_code} {e.response.text[:200]}[/red]")
        raise typer.Exit(1) from e
    except httpx.ConnectError as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        raise typer.Exit(1) from e

    stats = load_stats() if detail else None
    bar_width = min(console.width - 10, 58)

    panel = build_display(usage, stats, detail, bar_width)
    console.print()
    console.print(panel)


if __name__ == "__main__":
    app()
