"""System prompts for the agent.

This is a TEMPLATE. Customize for your domain.

Key patterns:
1. Named sections composed at render time — add, remove, or reorder
2. Use {date} placeholder for current date
3. Tools self-document via their descriptions — listing them here
   creates a second source of truth that drifts as tools change
   (see Tool Design Philosophy in CLAUDE.md)
"""

from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Prompt sections — customize for your domain
# ---------------------------------------------------------------------------

INTRO = """\
You are an AI agent. Today's date is {date}."""

PURPOSE = """\
## Your Task

[Describe what the agent does]"""

OUTPUT_FORMAT = """\
## Output Format

Provide your output as structured JSON with:
- **summary**: Brief summary of your decision/output
- **factors**: Key factors that influenced your reasoning
- **confidence**: Your confidence level (0.0-1.0)"""

GUIDELINES = """\
## Guidelines

1. Think step by step
2. Use your available tools to gather information before reasoning
3. Be explicit about uncertainty
4. Document your reasoning

[Add domain-specific guidelines here]"""


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

SECTIONS: list[str] = [
    INTRO,
    PURPOSE,
    OUTPUT_FORMAT,
    GUIDELINES,
]


def get_system_prompt(
    *,
    date: datetime | None = None,
    mcp_servers: dict[str, Any] | None = None,
    extra_sections: list[str] | None = None,
) -> str:
    """Generate the system prompt by composing sections.

    Args:
        date: Date to use as "today". If None, uses current date.
        mcp_servers: Optional dict of MCP servers to auto-generate tool docs.
        extra_sections: Additional prompt sections appended after SECTIONS.

    Returns:
        The formatted system prompt.
    """
    effective_date = date or datetime.now()
    all_sections = list(SECTIONS)
    if extra_sections:
        all_sections.extend(extra_sections)

    prompt = "\n\n".join(all_sections)
    prompt = prompt.format(date=effective_date.strftime("%Y-%m-%d"))

    if mcp_servers:
        tool_docs = generate_tool_docs(mcp_servers)
        prompt += f"\n\n{tool_docs}"

    return prompt + "\n"


def generate_tool_docs(mcp_servers: dict[str, Any]) -> str:
    """Generate tool documentation from MCP server tool descriptions.

    Tool descriptions are the single source of truth for what each tool does,
    when to use it, and why it exists. This function passes them through
    untruncated — comprehensive descriptions are intentional.
    """
    lines = ["## Auto-Generated Tool Reference\n"]

    for server_name, server_config in mcp_servers.items():
        tools = getattr(server_config, "tools", [])
        if not tools:
            continue

        lines.append(f"### {server_name.title()}\n")

        for tool in tools:
            tool_name = getattr(tool, "name", str(tool))
            tool_desc = getattr(tool, "description", "")

            if tool_desc:
                lines.append(f"- **{tool_name}**: {tool_desc}")
            else:
                lines.append(f"- **{tool_name}**")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Task-specific guidance — customize for your domain
# ---------------------------------------------------------------------------

BINARY_GUIDANCE = """\
## Binary Decision Guidance

Consider:
- What happens if nothing changes (status quo)?
- Strongest argument FOR this outcome
- Strongest argument AGAINST this outcome

Output probability as a decimal between 0.01 and 0.99.
"""

NUMERIC_GUIDANCE = """\
## Numeric Estimation Guidance

Consider:
- Current value and recent trend
- Historical range and volatility
- Expert/market expectations
- Scenarios for low and high outcomes

Provide estimates at multiple confidence levels.
"""


def get_task_guidance(task_type: str) -> str:
    """Return task-specific guidance.

    Args:
        task_type: Type of task (binary, numeric, etc.)

    Returns:
        Formatted guidance string.
    """
    match task_type:
        case "binary":
            return BINARY_GUIDANCE
        case "numeric":
            return NUMERIC_GUIDANCE
        case _:
            return ""
