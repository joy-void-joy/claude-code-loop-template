"""Scheduler for persistent agents.

Owns all async timing state: sleep/wake, debounce windows, scheduled
actions, reminders, and delayed actions. The environment layer (Discord
bot, game server, CLI) wires callbacks; the agent interacts through
MCP tools that delegate to this scheduler.

Usage:
    from lup.lib.realtime import Scheduler, ActionCallback

    async def send_message(content: str) -> None:
        await channel.send(content)

    scheduler = Scheduler(on_action=send_message)

    # Agent sleeps — blocks until wake event or timeout
    result = await scheduler.sleep(300)

    # Environment wakes agent on external event
    scheduler.wake("user_message")

See also: ``src/lup/agent/tools/realtime.py`` for the MCP tool
implementations that wrap this scheduler.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, cast

from pydantic import BaseModel, Field

from lup.lib.hooks import HooksConfig

logger = logging.getLogger(__name__)

ActionCallback = Callable[[str], Awaitable[None]]
"""Async callback for delivering actions (messages, commands, etc.)."""


# =====================================================================
# Tool input models
# =====================================================================


class SleepInput(BaseModel):
    """Input for the sleep tool."""

    seconds: int = Field(description="How long to sleep (max). Wakes early on events.")
    debounce_initial: int | None = Field(
        default=None,
        description=(
            "If set, start a debounce window: wait up to this many seconds "
            "for the first event before waking."
        ),
    )
    debounce_quiet: int | None = Field(
        default=None,
        description=(
            "Quiet period for debounce. Once activity starts, wait this long "
            "after each event before waking. Defaults to debounce_initial."
        ),
    )
    force: bool = Field(
        default=False,
        description="Bypass the pending-event guard (sleep even with unread events).",
    )


class DebounceInput(BaseModel):
    """Input for the debounce tool."""

    initial_seconds: int = Field(
        description="Wait up to this long for the first event."
    )
    quiet_seconds: int = Field(
        description="After first event, wait this long after each subsequent event."
    )


class RemindInput(BaseModel):
    """Input for the remind tool."""

    label: str = Field(description="What this reminder is about.")
    delay_seconds: int = Field(description="Seconds until the reminder fires.")


class ScheduleActionInput(BaseModel):
    """Input for the schedule_action tool."""

    content: str = Field(description="Content to deliver when the action fires.")
    delay_seconds: int = Field(
        description="Seconds to wait before firing (cancelled if an event arrives)."
    )


# =====================================================================
# Scheduler
# =====================================================================


class _PendingReminder(BaseModel):
    """A scheduled self-prompt."""

    task: asyncio.Task[None]
    label: str
    fire_at: float = Field(description="loop.time() when reminder fires")

    class Config:
        arbitrary_types_allowed = True


class Scheduler:
    """Manages all timed actions for a persistent agent session.

    All scheduling methods are non-blocking and return immediately.
    Only ``sleep()`` blocks — it waits for a wake event or timeout.

    The environment layer calls ``wake()`` and ``extend_debounce()``
    when external events arrive. The agent calls ``sleep()`` to yield
    and the various scheduling methods to plan future actions.
    """

    def __init__(
        self,
        *,
        on_action: ActionCallback,
        on_sleep: Callable[[], None] | None = None,
        ideas: list[str] | None = None,
    ) -> None:
        self._on_action = on_action
        self._on_sleep = on_sleep
        self._ideas: list[str] = ideas if ideas is not None else []

        # Wake mechanism
        self._wake: asyncio.Event = asyncio.Event()
        self._wake_reason: str | None = None

        # Debounce
        self._debounce_task: asyncio.Task[None] | None = None
        self._debounce_event: asyncio.Event = asyncio.Event()

        # Scheduled action
        self._scheduled_action_task: asyncio.Task[None] | None = None
        self._scheduled_action_content: str | None = None
        self._scheduled_action_fire_at: float | None = None

        # Reminders
        self._reminders: list[_PendingReminder] = []
        self._fired_reminder_labels: list[str] = []

        # Delayed actions
        self._pending_actions: list[tuple[asyncio.Task[None], str]] = []

        # Meta-before-sleep flag
        self.meta_recorded: bool = False

    @property
    def ideas(self) -> list[str]:
        """Cancelled actions and agent-captured threads."""
        return self._ideas

    # ------------------------------------------------------------------
    # Wake / Sleep
    # ------------------------------------------------------------------

    def wake(self, reason: str) -> None:
        """Wake the sleeping agent with a reason."""
        self._wake_reason = reason
        self._wake.set()

    async def sleep(self, seconds: int) -> dict[str, Any]:
        """Block until timer expires or a wake event fires.

        Debounce persists across sleep cycles — if active, events
        extend the quiet window and the next sleep waits for it.

        Returns a context dict with ``reason`` and scheduling state.
        """
        if self._on_sleep:
            self._on_sleep()

        if self._wake.is_set():
            pass  # Already have a pending wake — return immediately
        else:
            self._wake_reason = None
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=seconds)
            except asyncio.TimeoutError:
                self._wake_reason = "timer"

        self._wake.clear()
        return self._build_sleep_result()

    def _build_sleep_result(self) -> dict[str, Any]:
        """Build the minimal wake result."""
        result: dict[str, Any] = {
            "reason": self._wake_reason or "timer",
        }
        if self._fired_reminder_labels:
            result["fired_reminders"] = list(self._fired_reminder_labels)
            self._fired_reminder_labels.clear()
        return result

    # ------------------------------------------------------------------
    # Debounce
    # ------------------------------------------------------------------

    @property
    def debounce_active(self) -> bool:
        """Whether a debounce window is currently open."""
        return self._debounce_task is not None and not self._debounce_task.done()

    @property
    def wake_pending(self) -> bool:
        """Whether a wake event is already queued."""
        return self._wake.is_set()

    def start_debounce(self, initial_seconds: int, quiet_seconds: int) -> None:
        """Start a debounce window. Replaces any existing window.

        Phase 1 (initial): Wait up to ``initial_seconds`` for the first
        event. If nothing arrives, wake immediately.
        Phase 2 (quiet): Once activity is detected, wait ``quiet_seconds``
        after each event. Wake when the quiet period elapses.
        """
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._debounce_event.clear()

        # Absorb pending wake so sleep doesn't return immediately
        if self._wake.is_set():
            self._wake.clear()
            self._wake_reason = None
            self._debounce_event.set()

        self._debounce_task = asyncio.create_task(
            self._run_debounce(initial_seconds, quiet_seconds)
        )

    def extend_debounce(self) -> None:
        """Signal activity to reset the quiet timer."""
        if self.debounce_active:
            self._debounce_event.set()

    async def _run_debounce(self, initial_seconds: int, quiet_seconds: int) -> None:
        """Debounce timer: initial wait for activity, then quiet-period loop."""
        try:
            # Phase 1: wait for first activity
            try:
                await asyncio.wait_for(
                    self._debounce_event.wait(), timeout=initial_seconds
                )
            except asyncio.TimeoutError:
                self.wake("timer")
                return

            # Phase 2: quiet-period loop
            while True:
                self._debounce_event.clear()
                try:
                    await asyncio.wait_for(
                        self._debounce_event.wait(), timeout=quiet_seconds
                    )
                except asyncio.TimeoutError:
                    break
            self.wake("event")
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Scheduled action
    # ------------------------------------------------------------------

    def start_scheduled_action(self, content: str, delay: int) -> None:
        """Schedule an action that fires after delay if no event arrives.

        Only one at a time — calling again replaces the previous one.
        Cancelled actions are saved as ideas.
        """
        self.cancel_scheduled_action()
        self._scheduled_action_content = content
        self._scheduled_action_fire_at = asyncio.get_running_loop().time() + delay
        self._scheduled_action_task = asyncio.create_task(
            self._run_scheduled_action(content, delay)
        )

    def cancel_scheduled_action(self) -> None:
        """Cancel the pending scheduled action, saving it as an idea."""
        if self._scheduled_action_task and not self._scheduled_action_task.done():
            self._scheduled_action_task.cancel()
            if self._scheduled_action_content:
                self._ideas.append(self._scheduled_action_content)
        self._scheduled_action_content = None
        self._scheduled_action_fire_at = None
        self._scheduled_action_task = None

    async def _run_scheduled_action(self, content: str, delay: int) -> None:
        """Scheduled action coroutine. Fires but does NOT wake the agent."""
        try:
            await asyncio.sleep(delay)
            if self._on_sleep:
                self._on_sleep()
            await self._on_action(content)
            self._scheduled_action_content = None
            self._scheduled_action_fire_at = None
            self._scheduled_action_task = None
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------

    def add_reminder(self, label: str, delay: int) -> None:
        """Schedule a self-prompt reminder that wakes the agent."""
        fire_at = asyncio.get_running_loop().time() + delay
        task = asyncio.create_task(self._run_reminder(label, delay))
        self._reminders.append(
            _PendingReminder(task=task, label=label, fire_at=fire_at)
        )

    async def _run_reminder(self, label: str, delay: int) -> None:
        """Reminder coroutine. Records label and wakes agent."""
        try:
            await asyncio.sleep(delay)
            self._fired_reminder_labels.append(label)
            self.wake("reminder")
            self._reminders = [r for r in self._reminders if not r.task.done()]
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Delayed actions
    # ------------------------------------------------------------------

    def add_delayed_action(self, content: str, delay: int) -> None:
        """Schedule an action with a delay. Cancelled if an event arrives."""
        task = asyncio.create_task(self._run_delayed_action(content, delay))
        self._pending_actions.append((task, content))

    def cancel_delayed_actions(self) -> None:
        """Cancel all pending delayed actions, saving them as ideas."""
        for task, content in self._pending_actions:
            if not task.done():
                task.cancel()
                self._ideas.append(content)
        self._pending_actions.clear()

    async def _run_delayed_action(self, content: str, delay: int) -> None:
        """Delayed action coroutine."""
        try:
            await asyncio.sleep(delay)
            if self._on_sleep:
                self._on_sleep()
            await self._on_action(content)
            self._pending_actions = [
                (t, c) for t, c in self._pending_actions if not t.done()
            ]
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Event handlers (called by environment layer)
    # ------------------------------------------------------------------

    def on_external_event(self) -> None:
        """Cancel scheduled action + pending delayed actions on external event."""
        self.cancel_scheduled_action()
        self.cancel_delayed_actions()

    def on_agent_action(self) -> None:
        """Cancel scheduled action on agent's own action and require new meta."""
        self.cancel_scheduled_action()
        self.meta_recorded = False

    # ------------------------------------------------------------------
    # State for context tool
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return scheduling state for the context tool."""
        loop = asyncio.get_running_loop()
        now = loop.time()

        state: dict[str, Any] = {}

        if self._scheduled_action_task and not self._scheduled_action_task.done():
            remaining = max(0, int((self._scheduled_action_fire_at or now) - now))
            state["scheduled_action"] = {
                "content": self._scheduled_action_content,
                "remaining_seconds": remaining,
            }

        active_reminders = [r for r in self._reminders if not r.task.done()]
        self._reminders = active_reminders
        if active_reminders:
            state["pending_reminders"] = [
                {
                    "label": r.label,
                    "remaining_seconds": max(0, int(r.fire_at - now)),
                }
                for r in active_reminders
            ]

        state["debounce_active"] = self.debounce_active

        return state


# =====================================================================
# Hook factories
# =====================================================================


def create_stop_guard() -> HooksConfig:
    """Create a Stop hook that prevents the agent from ending its turn.

    The agent must use the ``sleep`` tool to yield control. This keeps
    the agent in a persistent loop: wake → act → sleep → wake.

    Returns:
        HooksConfig with a Stop hook.

    Usage:
        from lup.lib.realtime import create_stop_guard
        from lup.lib.hooks import merge_hooks

        hooks = merge_hooks(permission_hooks, create_stop_guard())
    """
    from claude_agent_sdk import HookInput, HookMatcher
    from claude_agent_sdk.types import HookContext, SyncHookJSONOutput

    async def stop_guard(
        input_data: HookInput,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> SyncHookJSONOutput:
        if input_data["hook_event_name"] != "Stop":
            return SyncHookJSONOutput()
        if input_data["stop_hook_active"]:
            return SyncHookJSONOutput()
        return SyncHookJSONOutput(
            decision="block",
            reason="You cannot end your turn. Use sleep to pause between turns.",
        )

    return cast(HooksConfig, {
        "Stop": [HookMatcher(hooks=[stop_guard])],
    })


def create_pending_event_guard(
    *,
    check_unread: Callable[[], int],
    scheduler: Scheduler,
    guarded_tools: list[str],
) -> HooksConfig:
    """Create a PreToolUse hook that blocks timing tools when unread events exist.

    Forces the agent to call ``context`` before sleeping or scheduling.

    Args:
        check_unread: Callable returning the count of unread events.
        scheduler: The Scheduler instance (checked for debounce/wake state).
        guarded_tools: MCP tool names to guard (e.g., ``["mcp__session__sleep"]``).

    Returns:
        HooksConfig with PreToolUse hooks.
    """
    from claude_agent_sdk import HookInput, HookMatcher
    from claude_agent_sdk.types import HookContext, SyncHookJSONOutput

    async def event_guard(
        input_data: HookInput,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> SyncHookJSONOutput:
        if input_data["hook_event_name"] != "PreToolUse":
            return SyncHookJSONOutput()
        tool_input = input_data["tool_input"]
        if tool_input.get("force", False):
            return SyncHookJSONOutput()
        if tool_input.get("debounce_initial") is not None:
            return SyncHookJSONOutput()
        if scheduler.debounce_active:
            return SyncHookJSONOutput()
        if scheduler.wake_pending:
            return SyncHookJSONOutput()

        unread = check_unread()
        if not unread:
            return SyncHookJSONOutput()

        return SyncHookJSONOutput(
            decision="block",
            reason=(f"Blocked — {unread} unread event(s). Call context first."),
        )

    return cast(HooksConfig, {
        "PreToolUse": [
            HookMatcher(matcher=tool_name, hooks=[event_guard])
            for tool_name in guarded_tools
        ],
    })


def create_meta_before_sleep_guard(
    *,
    scheduler: Scheduler,
    sleep_tool_name: str,
) -> HooksConfig:
    """Create a PreToolUse hook that requires meta before sleep.

    Forces the agent to call the ``meta`` tool (process self-assessment)
    before every sleep. Reset via ``scheduler.meta_recorded = False``
    after each agent action.

    Args:
        scheduler: The Scheduler instance.
        sleep_tool_name: MCP tool name for sleep (e.g., ``"mcp__session__sleep"``).

    Returns:
        HooksConfig with PreToolUse hooks.
    """
    from claude_agent_sdk import HookInput, HookMatcher
    from claude_agent_sdk.types import HookContext, SyncHookJSONOutput

    async def meta_guard(
        input_data: HookInput,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> SyncHookJSONOutput:
        if not scheduler.meta_recorded:
            return SyncHookJSONOutput(
                decision="block",
                reason=(
                    "You must call meta before sleeping. Assess your process this turn."
                ),
            )
        return SyncHookJSONOutput()

    return cast(HooksConfig, {
        "PreToolUse": [
            HookMatcher(matcher=sleep_tool_name, hooks=[meta_guard]),
        ],
    })
