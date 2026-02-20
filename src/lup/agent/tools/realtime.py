"""Real-time MCP tools for persistent agents.

This is a TEMPLATE. These tools show how to wire the Scheduler from
``lup.lib.realtime`` into an agent session. Customize for your domain.

The pattern:
1. Create a Scheduler with your environment's action callback
2. Define tools as closures bound to session state
3. Wire hooks (stop guard, pending event guard, meta guard)
4. Use streaming input mode with a single session-start turn

The tools here follow the harmon pattern:
- ``sleep`` is the ONLY blocking tool — all others return immediately
- ``context`` reads state and advances the event pointer
- ``reply`` delivers actions to the environment
- Timing tools (debounce, remind, schedule) are non-blocking

Tool descriptions are comprehensive because they're the agent's only
documentation. See Tool Design Philosophy in CLAUDE.md.
"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from claude_agent_sdk import tool

from lup.lib.realtime import (
    DebounceInput,
    RemindInput,
    ScheduleActionInput,
    Scheduler,
    SleepInput,
)
from lup.lib.responses import mcp_error, mcp_response


# =====================================================================
# Additional input models (domain-specific, customize these)
# =====================================================================


class ReplyMessageItem(BaseModel):
    """A single message in a reply batch."""

    message: str = Field(description="The message content.")
    delay_seconds: int = Field(
        default=0,
        description="Cumulative delay before sending (0 = immediate).",
    )


class ReplyInput(BaseModel):
    """Input for the reply tool."""

    messages: list[ReplyMessageItem] = Field(
        description="Messages to send, with optional staggered delays."
    )


class ContextInput(BaseModel):
    """Input for the context tool."""

    last_events: int = Field(
        default=5,
        description="Number of recent read events to include (0 = unread only).",
    )


class MetaInput(BaseModel):
    """Input for the meta tool."""

    thought: str = Field(
        description=(
            "Process self-assessment: pacing, timing, what worked, "
            "what you'd change. Required before sleep."
        )
    )


class NotesInput(BaseModel):
    """Input for the notes tool."""

    action: str = Field(description="One of: write, read, list, delete.")
    key: str = Field(default="", description="Note key.")
    content: str = Field(default="", description="Note content (for write).")


class IdeasInput(BaseModel):
    """Input for the ideas tool."""

    action: str = Field(description="One of: add, list, remove, set.")
    content: str = Field(default="", description="Idea text (for add).")
    index: int = Field(default=0, description="Index to remove (for remove).")
    ideas: list[str] = Field(
        default_factory=list, description="Full replacement list (for set)."
    )


# =====================================================================
# Tool factory
# =====================================================================


def create_realtime_tools(
    *,
    scheduler: Scheduler,
    build_context: Any,
    trace_logger: Any | None = None,
) -> list[Any]:
    """Create the standard set of real-time MCP tools.

    This is a TEMPLATE — customize for your domain. The tools are
    closures bound to the session state via the scheduler and
    build_context callback.

    Args:
        scheduler: The Scheduler instance for this session.
        build_context: Callable(last_events: int) -> dict that builds
            the context state and advances the read pointer.
        trace_logger: Optional TraceLogger for meta assessments.

    Returns:
        List of MCP tool functions.
    """

    # -- Communication tools -------------------------------------------

    @tool(
        "reply",
        "Deliver a message to the environment. Text output and thinking "
        "don't reach the user — this is the only way to communicate. "
        "One message is the default. For a sequence of short reactions "
        "you can batch with staggered delay_seconds. Delayed messages "
        "cancel if an external event arrives (cancelled text becomes an "
        "idea). Sending also cancels any pending scheduled_action.",
        ReplyInput.model_json_schema(),
    )
    async def reply_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = ReplyInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))

        sent = 0
        scheduled = 0
        cumulative_delay = 0
        for item in inp.messages:
            cumulative_delay += item.delay_seconds
            if cumulative_delay == 0:
                await scheduler._on_action(item.message)
                sent += 1
            else:
                scheduler.add_delayed_action(item.message, cumulative_delay)
                scheduled += 1

        if sent or scheduled:
            scheduler.on_agent_action()

        parts = []
        if sent:
            parts.append(f"{sent} sent")
        if scheduled:
            parts.append(f"{scheduled} scheduled")
        return mcp_response(", ".join(parts) + ".")

    @tool(
        "schedule_action",
        "Schedule an action that fires if the environment stays quiet for "
        "delay_seconds. Cancels (saved as idea) if an event arrives or "
        "you send a reply. Only one at a time — calling again replaces "
        "the previous one. Does not generate a new turn when it fires.",
        ScheduleActionInput.model_json_schema(),
    )
    async def schedule_action_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = ScheduleActionInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))
        scheduler.start_scheduled_action(inp.content, inp.delay_seconds)
        return mcp_response(f"Action scheduled in {inp.delay_seconds}s.")

    # -- Timing tools --------------------------------------------------

    @tool(
        "debounce",
        "Suppress wake events until activity stops. Two phases: waits "
        "up to initial_seconds for the first event; once activity starts, "
        "holds wake until quiet_seconds elapse with no new activity. "
        "Events still go to state — context works during debounce. "
        "Returns immediately. Only one debounce at a time — calling "
        "again replaces the previous one.",
        DebounceInput.model_json_schema(),
    )
    async def debounce_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = DebounceInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))
        scheduler.start_debounce(inp.initial_seconds, inp.quiet_seconds)
        return mcp_response(
            f"Debounce active: {inp.initial_seconds}s initial, "
            f"{inp.quiet_seconds}s quiet."
        )

    @tool(
        "sleep",
        "Pause until timer expires or an event occurs (external event, "
        "reminder). This is the ONLY blocking tool — all others return "
        "immediately. You MUST call meta before sleeping. Returns wake "
        "reason only — call context after waking to read state. "
        "No debounce by default — wakes immediately on events. "
        "Set debounce_initial/debounce_quiet to batch event bursts. "
        "Blocked when unread events exist — use force=true to bypass.",
        SleepInput.model_json_schema(),
    )
    async def sleep_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = SleepInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))

        if inp.debounce_initial is not None:
            scheduler.start_debounce(
                inp.debounce_initial,
                inp.debounce_quiet or inp.debounce_initial,
            )

        result = await scheduler.sleep(inp.seconds)
        result["time"] = datetime.now().strftime("%H:%M:%S")

        return mcp_response(json.dumps(result, indent=2))

    @tool(
        "remind",
        "Schedule a self-prompt that fires after delay_seconds. "
        "When it fires, it wakes you from sleep with fired_reminders "
        "in the result. Multiple reminders can be active simultaneously. "
        "Use for things you want to come back to — checking in, "
        "revisiting a topic, following up on something.",
        RemindInput.model_json_schema(),
    )
    async def remind_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = RemindInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))
        scheduler.add_reminder(inp.label, inp.delay_seconds)
        return mcp_response(f"Reminder '{inp.label}' set for {inp.delay_seconds}s.")

    # -- State tools ---------------------------------------------------

    @tool(
        "context",
        "Get current state and read new events. Returns timing info, "
        "environment state, and two separate lists: recent history and "
        "unread events (no overlap). Also returns scheduler state "
        "(pending actions, reminders, debounce). last_events controls "
        "history depth (default 5, 0 = unread only).",
        ContextInput.model_json_schema(),
    )
    async def context_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = ContextInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))
        result = build_context(inp.last_events)
        return mcp_response(json.dumps(result, indent=2))

    @tool(
        "notes",
        "Read or write private session notes. Not visible to the user.",
        NotesInput.model_json_schema(),
    )
    async def notes_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            NotesInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))

        # NOTE: This is a template. Wire to your session's notes dict.
        return mcp_response("Notes tool not wired. Customize in your session.")

    @tool(
        "ideas",
        "Capture threads worth exploring later. Cancelled actions "
        "automatically become ideas too. Use 'set' to replace the "
        "entire list after reorganizing.",
        IdeasInput.model_json_schema(),
    )
    async def ideas_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = IdeasInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))

        match inp.action:
            case "add":
                scheduler.ideas.append(inp.content)
                return mcp_response(f"Idea added ({len(scheduler.ideas)} total).")
            case "list":
                if not scheduler.ideas:
                    return mcp_response("No ideas.")
                lines = [f"{i}: {idea}" for i, idea in enumerate(scheduler.ideas)]
                return mcp_response("\n".join(lines))
            case "remove":
                if inp.index < 0 or inp.index >= len(scheduler.ideas):
                    return mcp_error(f"Invalid index {inp.index}. Use 'list' first.")
                removed = scheduler.ideas.pop(inp.index)
                return mcp_response(f"Removed: {removed}")
            case "set":
                scheduler.ideas.clear()
                scheduler.ideas.extend(inp.ideas)
                return mcp_response(f"Ideas replaced ({len(scheduler.ideas)} total).")
        return mcp_error(f"Unknown action: {inp.action}")

    @tool(
        "meta",
        "Record a process assessment for the improvement loop. "
        "What worked this turn? What was friction? Are you missing "
        "tools or information? Rate pacing, timing, quality. "
        "Be specific. Required before sleep.",
        MetaInput.model_json_schema(),
    )
    async def meta_tool(args: dict[str, Any]) -> dict[str, Any]:
        try:
            inp = MetaInput.model_validate(args)
        except ValidationError as e:
            return mcp_error(str(e))
        if trace_logger:
            trace_logger.log_text(inp.thought, heading="Meta")
        scheduler.meta_gate.mark_reflected()
        return mcp_response("Recorded.")

    return [
        reply_tool,
        schedule_action_tool,
        debounce_tool,
        sleep_tool,
        remind_tool,
        context_tool,
        notes_tool,
        ideas_tool,
        meta_tool,
    ]
