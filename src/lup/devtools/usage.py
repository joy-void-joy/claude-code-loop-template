"""Display Claude Code usage from the live API.

Calls the /api/oauth/usage endpoint for real-time utilization data
and supplements with stats-cache.json for daily detail.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, TypedDict

import httpx
import typer
from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(
    help="Claude Code live usage display",
    invoke_without_command=True,
)
console = Console()


# ── constants ──────────────────────────────────────────────

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

DAY_NAMES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


# ── API response types ─────────────────────────────────────


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


# ── stats cache models ─────────────────────────────────────


class DailyActivity(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date: str
    message_count: int = Field(alias="messageCount", default=0)
    session_count: int = Field(alias="sessionCount", default=0)
    tool_call_count: int = Field(alias="toolCallCount", default=0)


class DailyModelTokens(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date: str
    tokens_by_model: dict[str, int] = Field(alias="tokensByModel", default_factory=dict)


class ModelUsageEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    input_tokens: int = Field(alias="inputTokens", default=0)
    output_tokens: int = Field(alias="outputTokens", default=0)
    cache_read_input_tokens: int = Field(alias="cacheReadInputTokens", default=0)
    cache_creation_input_tokens: int = Field(
        alias="cacheCreationInputTokens", default=0
    )
    web_search_requests: int = Field(alias="webSearchRequests", default=0)
    cost_usd: float = Field(alias="costUSD", default=0)
    context_window: int = Field(alias="contextWindow", default=0)
    max_output_tokens: int = Field(alias="maxOutputTokens", default=0)


class LongestSession(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    session_id: str = Field(alias="sessionId")
    duration: int
    message_count: int = Field(alias="messageCount")
    timestamp: str


class StatsCache(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    version: int = 0
    last_computed_date: str = Field(alias="lastComputedDate", default="")
    daily_activity: list[DailyActivity] = Field(
        alias="dailyActivity", default_factory=list
    )
    daily_model_tokens: list[DailyModelTokens] = Field(
        alias="dailyModelTokens", default_factory=list
    )
    model_usage: dict[str, ModelUsageEntry] = Field(
        alias="modelUsage", default_factory=dict
    )
    total_sessions: int = Field(alias="totalSessions", default=0)
    total_messages: int = Field(alias="totalMessages", default=0)
    longest_session: LongestSession | None = Field(alias="longestSession", default=None)
    first_session_date: str = Field(alias="firstSessionDate", default="")
    hour_counts: dict[str, int] = Field(alias="hourCounts", default_factory=dict)
    total_speculation_time_saved_ms: int = Field(
        alias="totalSpeculationTimeSavedMs", default=0
    )


# ── display models ─────────────────────────────────────────


class PaceLabel(BaseModel):
    word: str
    style: str


class DailyBreakdown(BaseModel):
    date: str
    total_tokens: int
    tokens_by_model: dict[str, int]
    activity: DailyActivity | None


# ── pacing thresholds ──────────────────────────────────────

_PACE_COLOR_THRESHOLDS: list[tuple[float, str]] = [
    (0.7, "bright_green"),
    (1.0, "bright_cyan"),
    (1.3, "bright_yellow"),
]

_PACE_LABEL_THRESHOLDS: list[tuple[float, PaceLabel]] = [
    (0.5, PaceLabel(word="cruising", style="bold bright_green")),
    (0.85, PaceLabel(word="on track", style="bold bright_cyan")),
    (1.0, PaceLabel(word="on pace", style="bold bright_cyan")),
    (1.3, PaceLabel(word="ahead", style="bold bright_yellow")),
    (1.6, PaceLabel(word="running hot", style="bold bright_red")),
]
_PACE_LABEL_DEFAULT = PaceLabel(word="heavy usage", style="bold red")


# ── API ────────────────────────────────────────────────────


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
    data: UsageResponse = resp.json()
    return data


# ── stats cache ────────────────────────────────────────────


def load_stats() -> StatsCache | None:
    if not STATS_PATH.exists():
        return None
    try:
        return StatsCache.model_validate_json(STATS_PATH.read_bytes())
    except (ValueError, OSError):
        return None


def get_daily_breakdown(
    stats: StatsCache,
    window_start: datetime,
    window_end: datetime,
) -> list[DailyBreakdown]:
    """Get per-day token and activity breakdown for a time window."""
    tokens_by_date = {
        entry.date: entry.tokens_by_model for entry in stats.daily_model_tokens
    }
    activity_by_date = {entry.date: entry for entry in stats.daily_activity}

    days: list[DailyBreakdown] = []
    d = window_start.date()
    end = window_end.date()
    while d <= end:
        ds = d.isoformat()
        by_model = tokens_by_date.get(ds, {})
        days.append(
            DailyBreakdown(
                date=ds,
                total_tokens=sum(by_model.values()),
                tokens_by_model=by_model,
                activity=activity_by_date.get(ds),
            )
        )
        d += timedelta(days=1)
    return days


# ── formatting helpers ─────────────────────────────────────


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def fmt_countdown(dt: datetime) -> str:
    total_seconds = (dt - datetime.now(dt.tzinfo)).total_seconds()
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
    for threshold, color in _PACE_COLOR_THRESHOLDS:
        if ratio <= threshold:
            return color
    return "bright_red"


def pace_label(ratio: float) -> PaceLabel:
    for threshold, label in _PACE_LABEL_THRESHOLDS:
        if ratio <= threshold:
            return label
    return _PACE_LABEL_DEFAULT


def _place_label(text: str, position: int, line_width: int) -> str:
    """Place a text label at a horizontal position in a fixed-width line."""
    line = [" "] * line_width
    for j, ch in enumerate(text):
        pos = position + j
        if 0 <= pos < line_width:
            line[pos] = ch
    return "".join(line)


# ── rendering ──────────────────────────────────────────────


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

    pace = pace_label(ratio)

    out.append(f"  {label}", style="bold bright_white")
    out.append(f"  {utilization:.0f}%", style="bold")
    out.append(f"  ◆ {pace.word}", style=pace.style)
    out.append(f"  resets in {fmt_countdown(resets_at)}", style="dim")
    out.append("\n")

    render_bar(out, utilization, linear_pct, bar_width)

    line_width = bar_width + 2

    you_text = f"↑ you ({utilization:.0f}%)"
    you_pos = min(int((utilization / 100) * bar_width), bar_width - len(you_text))
    out.append(_place_label(you_text, you_pos, line_width), style="dim")
    out.append("\n")

    pace_text = f"↑ even ({linear_pct:.0f}%)"
    pace_pos = min(int((linear_pct / 100) * bar_width), line_width - len(pace_text))
    out.append(_place_label(pace_text, pace_pos, line_width), style="dim")
    out.append("\n")


def _render_overage(out: Text, extra: ExtraUsage, bar_width: int) -> None:
    """Render the extra usage (overage) section."""
    used = extra["used_credits"]
    limit = extra["monthly_limit"]
    util = extra["utilization"]

    out.append("  overage", style="bold bright_white")
    out.append(f"  ${used / 100:.2f}", style="bold")
    out.append(f" / ${limit / 100:.2f}", style="dim")
    out.append(f"  ({util:.0f}%)", style="bold")
    out.append("\n")

    fill_color = pace_color(util / 100)
    filled = min(int((util / 100) * bar_width), bar_width)
    out.append("  ")
    for i in range(bar_width):
        if i < filled:
            out.append("█", style=fill_color)
        else:
            out.append("░", style="bright_black")
    out.append("\n\n")


def _render_daily_breakdown(
    out: Text,
    seven_day: UsageBucket,
    stats: StatsCache,
    bar_width: int,
) -> None:
    """Render the per-day cost-weighted breakdown within the 7-day window."""
    resets_at = datetime.fromisoformat(seven_day["resets_at"])
    window_start = resets_at - timedelta(days=7)
    today = datetime.now(resets_at.tzinfo).date()

    daily = get_daily_breakdown(stats, window_start, resets_at)
    if not any(d.total_tokens > 0 for d in daily):
        return

    out.append("  per day", style="bold bright_white")
    if stats.last_computed_date and stats.last_computed_date < today.isoformat():
        out.append(f"  (cache: {stats.last_computed_date})", style="dim italic")
    out.append("\n")

    day_bar_w = bar_width - 14

    cost_rates: dict[str, float] = {}
    for mid, entry in stats.model_usage.items():
        total_tok = (
            entry.input_tokens
            + entry.output_tokens
            + entry.cache_read_input_tokens
            + entry.cache_creation_input_tokens
        )
        if total_tok > 0:
            cost_rates[mid] = entry.cost_usd / total_tok

    model_totals: dict[str, int] = {}
    week_total = 0
    daily_weights: list[float] = []
    for day in daily:
        week_total += day.total_tokens
        weight = sum(
            tokens * cost_rates.get(model, 0)
            for model, tokens in day.tokens_by_model.items()
        )
        for model, tokens in day.tokens_by_model.items():
            model_totals[model] = model_totals.get(model, 0) + tokens
        daily_weights.append(weight)

    weekly_util = seven_day["utilization"]
    week_weight = sum(daily_weights)
    if cost_rates and week_weight > 0 and weekly_util > 0:
        weekly_budget = week_weight / (weekly_util / 100)
    else:
        weekly_budget = (
            week_total / (weekly_util / 100) if weekly_util > 0 else max(week_total, 1)
        )
        daily_weights = [float(d.total_tokens) for d in daily]

    cumulative_used = 0.0
    daily_budgets: list[float] = []
    n_days = len(daily)
    for i, day in enumerate(daily):
        d = datetime.fromisoformat(day.date).date()
        remaining = max(n_days - i, 1)
        daily_budgets.append((weekly_budget - cumulative_used) / remaining)
        if d <= today:
            cumulative_used += daily_weights[i]

    for i, day in enumerate(daily):
        d = datetime.fromisoformat(day.date).date()
        day_name = DAY_NAMES[d.weekday()]

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
            continue

        actual = daily_weights[i]
        budget = daily_budgets[i]
        fill_frac = actual / weekly_budget if weekly_budget > 0 else 0
        pace_frac = budget / weekly_budget if weekly_budget > 0 else 0
        fill_pos = min(int(fill_frac * day_bar_w), day_bar_w)
        pace_pos = min(max(int(pace_frac * day_bar_w), 0), day_bar_w - 1)
        ratio = actual / budget if budget > 0 else (2.0 if actual > 0 else 0)
        color = pace_color(ratio)
        overflow_color = "bright_red" if ratio > 1.3 else "bright_yellow"

        for j in range(day_bar_w):
            if j == pace_pos:
                if j < fill_pos:
                    out.append("▎", style="bold white on " + color)
                else:
                    out.append("▎", style="bold bright_white")
            elif j < fill_pos and j <= pace_pos:
                out.append("█", style=color)
            elif j < fill_pos:
                out.append("▒", style=overflow_color)
            elif j < pace_pos:
                out.append("░", style="bright_black")
            else:
                out.append("░", style="black")

        out.append(f" {fmt_tokens(day.total_tokens):>5}", style="bold")
        if day.activity and day.activity.message_count > 0:
            out.append(f"  {day.activity.message_count:,}m", style="dim")
        out.append("\n")

    out.append("\n")

    if model_totals:
        out.append("  models", style="bold bright_white")
        out.append("  ")
        for model, tokens in sorted(
            model_totals.items(), key=lambda x: x[1], reverse=True
        ):
            name = MODEL_NAMES.get(model, model)
            pct = tokens / week_total * 100 if week_total > 0 else 0
            out.append(f"● {name} ", style=model_color(model))
            out.append(f"{pct:.0f}%  ", style="dim")
        out.append("\n")


# ── display assembly ───────────────────────────────────────


def build_display(
    usage: UsageResponse,
    stats: StatsCache | None,
    show_detail: bool,
    bar_width: int,
) -> Panel:
    out = Text()

    seven_day = usage.get("seven_day")
    if seven_day and seven_day.get("resets_at"):
        render_bucket(out, "weekly", seven_day, 7 * 24, bar_width)
        out.append("\n")

    five_hour = usage.get("five_hour")
    if five_hour and five_hour.get("resets_at"):
        render_bucket(out, "5-hour", five_hour, 5, bar_width)
        out.append("\n")

    for label, bucket in [
        ("opus 7d", usage.get("seven_day_opus")),
        ("sonnet 7d", usage.get("seven_day_sonnet")),
        ("cowork 7d", usage.get("seven_day_cowork")),
        ("oauth 7d", usage.get("seven_day_oauth_apps")),
    ]:
        if bucket and bucket.get("resets_at"):
            render_bucket(out, label, bucket, 7 * 24, bar_width)
            out.append("\n")

    extra = usage.get("extra_usage")
    if extra and extra["is_enabled"]:
        _render_overage(out, extra, bar_width)

    if show_detail and stats and seven_day and seven_day.get("resets_at"):
        _render_daily_breakdown(out, seven_day, stats, bar_width)

    return Panel(
        out,
        title="[bold bright_white]Claude Code Usage[/bold bright_white]",
        border_style="bright_cyan",
        padding=(1, 1),
    )


def _fetch_and_build(detail: bool, bar_width: int) -> Panel:
    """Fetch usage and build the display panel."""
    usage = fetch_usage()
    stats = load_stats() if detail else None
    return build_display(usage, stats, detail, bar_width)


def _build_error_panel(message: str) -> Panel:
    out = Text()
    out.append(f"  {message}", style="red")
    out.append("\n  retrying...", style="dim")
    return Panel(
        out,
        title="[bold bright_white]Claude Code Usage[/bold bright_white]",
        border_style="red",
        padding=(1, 1),
    )


# ── CLI ────────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def main(
    detail: Annotated[
        bool,
        typer.Option(
            "--detail/--no-detail",
            help="Show daily breakdown from stats cache.",
        ),
    ] = True,
    watch: Annotated[
        bool,
        typer.Option(
            "--watch",
            "-w",
            help="Continuously refresh the display.",
        ),
    ] = True,
    interval: Annotated[
        int,
        typer.Option(
            "--interval",
            "-n",
            help="Refresh interval in seconds (with --watch).",
        ),
    ] = 600,
) -> None:
    """Show live Claude Code usage with pacing bars."""
    if not CREDS_PATH.exists():
        console.print("[red]No credentials at ~/.claude/.credentials.json[/red]")
        raise typer.Exit(1)

    bar_width = min(console.width - 10, 58)

    if not watch:
        try:
            panel = _fetch_and_build(detail, bar_width)
        except httpx.HTTPStatusError as e:
            console.print(
                f"[red]API error: {e.response.status_code}"
                f" {e.response.text[:200]}[/red]"
            )
            raise typer.Exit(1) from e
        except httpx.ConnectError as e:
            console.print(f"[red]Connection failed: {e}[/red]")
            raise typer.Exit(1) from e
        console.print()
        console.print(panel)
        return

    timestamp = Text(
        f"  updated {datetime.now().strftime('%H:%M:%S')}"
        f"  ·  every {interval}s  ·  ctrl-c to quit",
        style="dim",
    )
    try:
        panel = _fetch_and_build(detail, bar_width)
    except (httpx.HTTPStatusError, httpx.ConnectError):
        panel = _build_error_panel("Initial fetch failed")

    with Live(
        Group(panel, timestamp),
        console=console,
        refresh_per_second=1,
        screen=True,
    ) as live:
        while True:
            try:
                time.sleep(interval)
                panel = _fetch_and_build(detail, bar_width)
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                panel = _build_error_panel(str(e)[:120])
            except KeyboardInterrupt:
                break
            timestamp = Text(
                f"  updated {datetime.now().strftime('%H:%M:%S')}"
                f"  ·  every {interval}s  ·  ctrl-c to quit",
                style="dim",
            )
            live.update(Group(panel, timestamp))
