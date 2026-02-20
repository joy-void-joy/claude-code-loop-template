"""Reflection tool — forced self-assessment before output finalization.

This is a TEMPLATE. Customize the input model and reviewer prompt
for your domain.

Pattern: A tool the agent calls to record its self-assessment before
producing final output. A :class:`~lup.lib.reflect.ReflectionGate`
hook enforces this — StructuredOutput (or sleep) is denied until
the agent has called ``review``.

Optionally runs a reviewer sub-agent (independent ClaudeSDKClient)
that critiques the main agent's reasoning with sandboxed file access
to past outputs and web search.

Usage in core.py:
    1. Call ``create_reflect_tools(session_dir=..., outputs_dir=...)``
    2. Register the tools as an MCP server
    3. Wire ``create_reflection_gate(gate=kit["gate"], ...)`` into hooks

Tool naming convention:
    After registration: ``mcp__{server_name}__review``
    Example: ``mcp__notes__review``
"""

import json
import logging
from pathlib import Path
from typing import Any, TypedDict

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, TextBlock
from pydantic import BaseModel, Field

from lup.lib import LupMcpTool, ResponseCollector, lup_tool, mcp_success, tracked
from lup.lib.reflect import ReflectionGate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reviewer system prompt (customize for your domain)
# ---------------------------------------------------------------------------

_REVIEWER_SYSTEM_PROMPT = """\
You review the main agent's output before it is finalized. Your job is \
to catch errors in reasoning, gaps in research, and miscalibrated confidence.

## What to flag

**Overconfidence:**
- Conclusions not supported by the evidence gathered
- Important counterarguments or alternative explanations ignored
- Small sample size or weak sources treated as definitive

**Underconfidence:**
- Strong evidence hedged unnecessarily
- Clear patterns dismissed as uncertain
- Excessive caveats when the data is consistent

**Research gaps:**
- Evidence from a single source or angle when multiple exist
- Obvious avenues not explored (check the trace)
- Key data sources overlooked for this domain

**Logic errors:**
- Contradictions between stated reasoning and conclusions
- Factors pulling in opposite directions without resolution
- Missing steps in the argument chain

If you don't find real issues, say so briefly and stop. Don't fabricate \
concerns to appear thorough.

## Historical data

You have Read, Glob, and Grep access to past outputs at:

  {outputs_dir}/

Use these to check calibration patterns: how accurate were past outputs \
in similar situations?

## Format

Reply with a brief structured critique. Be direct and specific — cite \
the exact claim, factor, or number you're questioning.
"""


# ---------------------------------------------------------------------------
# Input model (customize for your domain)
# ---------------------------------------------------------------------------


class ReflectInput(BaseModel):
    """Input for the reflection tool. Customize fields for your domain.

    Add domain-specific fields here (e.g., factors with logits for
    forecasting, move evaluation for game playing).
    """

    assessment: str = Field(
        description=(
            "Freeform narrative assessment of the work so far. "
            "Structure however feels natural for this particular task."
        ),
    )
    confidence: float = Field(
        description="Your confidence in the current output (0.0-1.0).",
    )
    key_uncertainties: str | None = Field(
        default=None,
        description="What you're most uncertain about and what would change your mind.",
    )
    tool_audit: str = Field(
        description=(
            "Which tools provided useful information, which returned "
            "empty results, and which had actual failures."
        ),
    )
    process_reflection: str = Field(
        description=(
            "How did the system feel to use — not what you did, but how the "
            "scaffolding supported you. What felt rigid or lacking, what felt "
            "smooth? Where did you hit friction — a tool returning unhelpful "
            "output, a forced workaround, a missing capability?"
        ),
    )
    skip_reviewer: bool = Field(
        default=False,
        description="Skip the reviewer sub-agent (e.g., for speed or when trivial).",
    )


# ---------------------------------------------------------------------------
# Reviewer sub-agent
# ---------------------------------------------------------------------------


async def _run_reviewer(
    validated: ReflectInput,
    outputs_dir: Path | None,
) -> str | None:
    """Run the reviewer sub-agent and return its critique text."""
    prompt_sections = [
        "## Agent Assessment\n\n" + validated.assessment,
        f"## Confidence: {validated.confidence:.0%}",
    ]
    if validated.key_uncertainties:
        prompt_sections.append(
            "## Key Uncertainties\n\n" + validated.key_uncertainties
        )

    reviewer_prompt = "\n\n".join(prompt_sections)

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        system_prompt=_REVIEWER_SYSTEM_PROMPT.format(
            outputs_dir=outputs_dir or "N/A",
        ),
        max_thinking_tokens=8000,
        permission_mode="bypassPermissions",
        tools=["Read", "Glob", "Grep", "WebFetch"],
        max_turns=5,
        extra_args={"no-session-persistence": None},
    )

    collector = ResponseCollector(prefix="  ↳ [reviewer] ")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(reviewer_prompt)
        await collector.collect(client)

    texts = [b.text for b in collector.blocks if isinstance(b, TextBlock)]
    return "\n\n".join(texts) if texts else None


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


class ReflectToolKit(TypedDict):
    """Return type for :func:`create_reflect_tools`."""

    tools: list[LupMcpTool]
    gate: ReflectionGate


def create_reflect_tools(
    *,
    session_dir: Path,
    outputs_dir: Path | None = None,
) -> ReflectToolKit:
    """Create the reflection tool(s) and their gate state.

    Returns both the tools (for MCP server registration) and the
    gate (for wiring into :func:`~lup.lib.reflect.create_reflection_gate`).

    Args:
        session_dir: Where to save the review output (JSON).
        outputs_dir: Path to past outputs for the reviewer to Read.
            If None, the reviewer won't have historical data access.
    """
    gate = ReflectionGate()

    @lup_tool(
        "review",
        (
            "Structured self-review before finalizing output. Call this tool "
            "after completing your research and analysis but before producing "
            "your final structured output. Runs an independent reviewer that "
            "critiques your reasoning, checks for gaps, and flags calibration "
            "issues. Use the reviewer's feedback to adjust your output. "
            "You must call this at least once per session."
        ),
        ReflectInput,
    )
    @tracked("review")
    async def review(args: dict[str, Any]) -> dict[str, Any]:
        validated = ReflectInput.model_validate(args)

        # Save the review input
        session_dir.mkdir(parents=True, exist_ok=True)
        review_path = session_dir / "review.json"
        review_path.write_text(
            json.dumps(validated.model_dump(), indent=2), encoding="utf-8"
        )

        gate.mark_reflected()

        critique: str | None = None
        if not validated.skip_reviewer:
            try:
                critique = await _run_reviewer(validated, outputs_dir)
            except Exception:
                logger.exception("Reviewer sub-agent failed")
                critique = None

        result: dict[str, str | bool] = {
            "status": "reviewed",
            "assessment_saved": str(review_path),
            "process_reflection": validated.process_reflection,
            "tool_audit": validated.tool_audit,
        }
        if critique:
            result["reviewer_critique"] = critique
        else:
            result["reviewer_critique"] = "(skipped or failed)"

        return mcp_success(result)

    return ReflectToolKit(tools=[review], gate=gate)
