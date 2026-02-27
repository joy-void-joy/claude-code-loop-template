"""Tool call metrics tracking.

Provides a decorator that tracks tool call counts, durations, and errors.
Metrics are saved with each session for feedback loop analysis.

Usage:
    @tracked("my_tool")
    async def my_tool(args: MyToolInput) -> dict:
        ...

    # At end of session
    metrics = get_metrics_summary()
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import TypedDict, cast

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolMetricsDict(TypedDict):
    """Serialized metrics for a single tool."""

    call_count: int
    error_count: int
    error_rate: str
    total_duration_ms: float
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float


class MetricsSummary(TypedDict):
    """Serialized summary of all tool metrics."""

    session_duration_seconds: float
    total_tool_calls: int
    total_errors: int
    overall_error_rate: str
    total_tool_time_ms: float
    tools_used: int
    by_tool: dict[str, ToolMetricsDict]


class ToolMetrics(BaseModel):
    """Metrics for a single tool."""

    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        """Average duration per call in milliseconds."""
        if self.call_count == 0:
            return 0.0
        return self.total_duration_ms / self.call_count

    @property
    def error_rate(self) -> float:
        """Percentage of calls that resulted in errors."""
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count

    def record_call(self, duration_ms: float, is_error: bool = False) -> None:
        """Record a tool call."""
        self.call_count += 1
        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        if is_error:
            self.error_count += 1

    def to_dict(self) -> ToolMetricsDict:
        """Convert to dictionary for serialization."""
        return ToolMetricsDict(
            call_count=self.call_count,
            error_count=self.error_count,
            error_rate=f"{self.error_rate:.1%}",
            total_duration_ms=round(self.total_duration_ms, 2),
            avg_duration_ms=round(self.avg_duration_ms, 2),
            min_duration_ms=(
                round(self.min_duration_ms, 2)
                if self.min_duration_ms != float("inf")
                else 0
            ),
            max_duration_ms=round(self.max_duration_ms, 2),
        )


class MetricsCollector:
    """Collects metrics for all tools."""

    def __init__(self) -> None:
        self.metrics: dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.session_start: float = time.time()

    def record(
        self, tool_name: str, duration_ms: float, is_error: bool = False
    ) -> None:
        """Record a tool call."""
        self.metrics[tool_name].record_call(duration_ms, is_error)

    def get_summary(self) -> MetricsSummary:
        """Get a summary of all metrics."""
        total_calls = sum(m.call_count for m in self.metrics.values())
        total_errors = sum(m.error_count for m in self.metrics.values())
        total_duration = sum(m.total_duration_ms for m in self.metrics.values())
        session_duration = time.time() - self.session_start

        return MetricsSummary(
            session_duration_seconds=round(session_duration, 2),
            total_tool_calls=total_calls,
            total_errors=total_errors,
            overall_error_rate=f"{total_errors / max(1, total_calls):.1%}",
            total_tool_time_ms=round(total_duration, 2),
            tools_used=len(self.metrics),
            by_tool={name: m.to_dict() for name, m in self.metrics.items()},
        )

    def log_summary(self, level: int = logging.INFO) -> None:
        """Log a summary of all metrics."""
        summary = self.get_summary()
        logger.log(
            level,
            "Tool Metrics: %d calls, %d errors, %.1fs session",
            summary["total_tool_calls"],
            summary["total_errors"],
            summary["session_duration_seconds"],
        )

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.session_start = time.time()


# Global metrics collector
collector = MetricsCollector()


def tracked[**P, T](
    tool_name: str | None = None,
) -> Callable[
    [Callable[P, Coroutine[object, object, T]]],
    Callable[P, Coroutine[object, object, T]],
]:
    """Decorator to track tool call metrics.

    Args:
        tool_name: Name to record metrics under. If None, uses function name.

    Example:
        @tracked("search")
        async def search(args: SearchInput) -> dict:
            ...
    """

    def decorator(
        func: Callable[P, Coroutine[object, object, T]],
    ) -> Callable[P, Coroutine[object, object, T]]:
        name = tool_name or func.__name__

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time.perf_counter()
            is_error = False

            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict) and cast(dict[str, object], result).get(
                    "is_error"
                ):
                    is_error = True
                return result
            except BaseException:
                is_error = True
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                collector.record(name, duration_ms, is_error)

        return wrapper

    return decorator


def log_metrics_summary() -> None:
    """Log a summary of all tool metrics."""
    collector.log_summary()


def get_metrics_summary() -> MetricsSummary:
    """Get a summary of all tool metrics."""
    return collector.get_summary()


def reset_metrics() -> None:
    """Reset all tool metrics."""
    collector.reset()
