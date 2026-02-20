"""Main agent orchestration.

This is a TEMPLATE. Customize for your domain.

Key patterns:
1. Use ClaudeAgentOptions with structured output
2. Create MCP servers with create_mcp_server()
3. Track tool metrics with the @tracked decorator
4. Save sessions for feedback loop analysis
5. Use hooks for permission control
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import cast

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ContentBlock,
    TextBlock,
    ToolUseBlock,
)

from claude_agent_sdk.types import McpSdkServerConfig

from lup.agent.config import settings
from lup.agent.models import AgentOutput, SessionResult, TokenUsage, get_output_schema
from lup.agent.prompts import get_system_prompt
from lup.agent.subagents import get_subagents
from lup.agent.tool_policy import ToolPolicy
from lup.agent.tools.example import EXAMPLE_TOOLS
from lup.agent.tools.reflect import create_reflect_tools
from lup.version import AGENT_VERSION
from lup.lib import (
    NotesConfig,
    ResponseCollector,
    Sandbox,
    TraceLogger,
    create_permission_hooks,
    create_reflection_gate,
    create_sdk_mcp_server,
    extract_sdk_tools,
    merge_hooks,
    get_metrics_summary,
    log_metrics_summary,
    reset_metrics,
    save_session,
    setup_notes,
)

logger = logging.getLogger(__name__)

NOTES_PATH = Path("./notes")
TRACES_PATH = NOTES_PATH / "traces"


def _build_options(
    notes_config: NotesConfig,
    *,
    sandbox_server: McpSdkServerConfig | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions from settings and notes config.

    Separated from run_agent() so the option-building logic can be
    tested and customized independently.
    """
    # Create MCP servers for your tools
    # TODO: Replace with your actual tool servers
    example_server = create_sdk_mcp_server(
        name="example",
        version="1.0.0",
        tools=extract_sdk_tools(EXAMPLE_TOOLS),
    )

    # Reflection tools — forced self-review before structured output
    reflect_kit = create_reflect_tools(
        session_dir=notes_config.session,
        outputs_dir=notes_config.output.parent,
    )
    reflect_server = create_sdk_mcp_server(
        name="notes",
        version="1.0.0",
        tools=extract_sdk_tools(reflect_kit["tools"]),
    )

    # Collect all MCP servers to register
    additional_servers: list[McpSdkServerConfig] = [example_server, reflect_server]
    if sandbox_server is not None:
        additional_servers.append(sandbox_server)

    policy = ToolPolicy.from_settings(settings)
    permission_hooks = create_permission_hooks(notes_config.rw, notes_config.ro)

    # Reflection gate: deny StructuredOutput until agent calls review
    gate_hooks = create_reflection_gate(
        gate=reflect_kit["gate"],
        gated_tool="StructuredOutput",
        reflection_tool_name="mcp__notes__review",
    )
    hooks = merge_hooks(permission_hooks, gate_hooks)

    return ClaudeAgentOptions(
        model=settings.model,
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": get_system_prompt(),
        },
        max_thinking_tokens=settings.max_thinking_tokens or (128_000 - 1),
        permission_mode="bypassPermissions",
        extra_args={"no-session-persistence": None},
        hooks=hooks,
        sandbox={
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
        },
        mcp_servers=policy.get_mcp_servers(*additional_servers),
        agents=get_subagents(),
        add_dirs=[str(d) for d in notes_config.all_dirs],
        allowed_tools=policy.get_allowed_tools(),
        output_format={
            "type": "json_schema",
            "schema": get_output_schema(),
        },
    )


async def run_agent(
    task: str,
    *,
    session_id: str | None = None,
    task_id: str | None = None,
) -> SessionResult:
    """Run the agent on a task.

    Args:
        task: The task/prompt for the agent.
        session_id: Unique identifier for this session. Auto-generated if None.
        task_id: Optional task identifier (e.g., question ID for forecasting).

    Returns:
        SessionResult with the agent's output and metadata.
    """
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("Starting session %s", session_id)
    reset_metrics()

    notes = setup_notes(session_id, task_id or "0")
    trace_path = TRACES_PATH / session_id / f"{datetime.now().strftime('%H%M%S')}.md"
    trace_logger = TraceLogger(trace_path=trace_path, title=f"Session {session_id}")

    # --- Sandbox (optional, requires Docker) ---
    # Customize: adjust pre_install, timeout, network_mode, or remove entirely
    # if your agent doesn't need code execution.
    sandbox = Sandbox(
        session_id=session_id,
        shared_dir=notes.session / "sandbox_shared",
        timeout_seconds=settings.sandbox_timeout_seconds,
    )

    collector = ResponseCollector(trace_logger=trace_logger)

    with sandbox:
        options = _build_options(notes, sandbox_server=sandbox.create_mcp_server())

        async with ClaudeSDKClient(options=options) as client:
            await client.query(task)
            await collector.collect(client)

    trace_logger.save()
    log_metrics_summary()

    session_result = _build_result(
        session_id=session_id,
        task_id=task_id,
        collector=collector,
    )

    save_session(session_result, session_id=session_result.session_id)

    return session_result


def _build_result(
    *,
    session_id: str,
    task_id: str | None,
    collector: ResponseCollector,
) -> SessionResult:
    """Build a SessionResult from the completed agent run."""
    result = collector.result
    if result is None:
        raise RuntimeError("No result in collector")

    output = AgentOutput(summary="No output produced", factors=[], confidence=0.5)
    if result.structured_output:
        output = AgentOutput.model_validate(result.structured_output)

    return SessionResult(
        session_id=session_id,
        task_id=task_id,
        agent_version=AGENT_VERSION,
        timestamp=datetime.now().isoformat(),
        output=output,
        reasoning="".join(
            b.text for b in collector.blocks if isinstance(b, TextBlock)
        ),
        sources_consulted=_extract_sources(collector.blocks),
        duration_seconds=(result.duration_ms / 1000) if result.duration_ms else None,
        cost_usd=result.total_cost_usd,
        token_usage=cast(TokenUsage, result.usage) if result.usage else None,
        tool_metrics=get_metrics_summary(),
    )


def _extract_sources(blocks: list[ContentBlock]) -> list[str]:
    """Extract source URLs/queries from tool use blocks."""
    sources: list[str] = []
    for block in blocks:
        if isinstance(block, ToolUseBlock) and block.name in (
            "WebSearch",
            "WebFetch",
        ):
            if isinstance(block.input, dict):
                source = block.input.get("url") or block.input.get("query")
                if source:
                    sources.append(str(source))
    return sources
