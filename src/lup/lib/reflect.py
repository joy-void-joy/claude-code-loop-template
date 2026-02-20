"""Reflection gate abstraction for enforcing reflect-before-output patterns.

Agents benefit from structured self-assessment before committing to output.
This module provides the domain-neutral gate mechanism:

- ``ReflectionGate``: Flag-based state tracker for whether the agent
  has reflected in the current cycle.
- ``create_reflection_gate()``: Hook factory that denies a target tool
  (e.g., ``StructuredOutput``, ``sleep``) until reflection is recorded.

The reflection *tool* and its input model are domain-specific and belong
in ``agent/tools/``. This module only provides the enforcement mechanism.

One-shot agents: gate ``StructuredOutput`` on reflection.
Persistent agents: gate ``sleep`` on reflection (via ``Scheduler.meta_gate``).

Usage::

    from lup.lib import ReflectionGate, create_reflection_gate, merge_hooks

    gate = ReflectionGate()
    gate_hooks = create_reflection_gate(
        gate=gate,
        gated_tool="StructuredOutput",
        reflection_tool_name="mcp__notes__review",
    )
    hooks = merge_hooks(permission_hooks, gate_hooks)

    # In the reflection tool handler:
    gate.mark_reflected()

    # For persistent agents, reset per cycle:
    gate.reset()
"""

from typing import cast

from claude_agent_sdk import HookInput, HookMatcher
from claude_agent_sdk.types import HookContext, SyncHookJSONOutput

from lup.lib.hooks import HooksConfig


class ReflectionGate:
    """Tracks whether the agent has reflected in the current cycle.

    Used by :func:`create_reflection_gate` to enforce "reflect before X"
    patterns. The reflection tool handler calls :meth:`mark_reflected`
    after saving reflection data. The orchestration layer calls
    :meth:`reset` when a new cycle begins (e.g., after each agent action
    in persistent mode).
    """

    __slots__ = ("_reflected",)

    def __init__(self) -> None:
        self._reflected: bool = False

    @property
    def reflected(self) -> bool:
        """Whether reflection has been recorded this cycle."""
        return self._reflected

    def mark_reflected(self) -> None:
        """Record that reflection has occurred."""
        self._reflected = True

    def reset(self) -> None:
        """Require fresh reflection (start of new cycle)."""
        self._reflected = False


def create_reflection_gate(
    *,
    gate: ReflectionGate,
    gated_tool: str,
    reflection_tool_name: str = "reflection",
    denial_message: str | None = None,
) -> HooksConfig:
    """Create a PreToolUse hook that denies *gated_tool* until reflection.

    The hook checks ``gate.reflected``. If ``False``, denies *gated_tool*
    with a message telling the agent to call *reflection_tool_name* first.

    .. note::

        If you also need to rewrite the gated tool's input (e.g., unwrap
        a ``{"parameter": {...}}`` wrapper), combine both checks in a
        single hook to avoid the CLI bug where multiple PreToolUse hooks
        overwrite each other's ``updatedInput`` (SDK issue #15897).
        Register this gate as the **last** PreToolUse hook.

    Args:
        gate: The :class:`ReflectionGate` instance tracking status.
        gated_tool: Tool name to block (e.g., ``"StructuredOutput"``).
        reflection_tool_name: Name shown in the denial message.
        denial_message: Custom denial text. Uses a sensible default
            if ``None``.

    Returns:
        HooksConfig with a PreToolUse hook.
    """
    default_message = (
        f"You must call {reflection_tool_name}() with your assessment "
        f"BEFORE calling {gated_tool}. Reflect on your work first, "
        f"then try again."
    )
    message = denial_message or default_message

    async def reflection_gate_hook(
        input_data: HookInput,
        _tool_use_id: str | None,
        _context: HookContext,
    ) -> SyncHookJSONOutput:
        if gate.reflected:
            return SyncHookJSONOutput(
                hookSpecificOutput={
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            )
        return SyncHookJSONOutput(
            hookSpecificOutput={
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": message,
            }
        )

    return cast(
        HooksConfig,
        {
            "PreToolUse": [
                HookMatcher(matcher=gated_tool, hooks=[reflection_gate_hook])
            ],
        },
    )
