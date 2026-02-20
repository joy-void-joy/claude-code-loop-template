"""Agent introspection and interactive debugging tools.

Commands:
- inspect: Pretty-print the full agent configuration (tools, schemas, prompt, subagents)
- serve-tools: Start SDK tools as an MCP stdio server (used by ``chat``)
- chat: Launch an interactive ``claude`` session with the agent's tools and prompt
- repl: Interactive REPL with the agent via the SDK (continuous session)
"""

import asyncio
import inspect as inspect_mod
import io
import json
import logging
import os
import sys
import tempfile
from typing import Annotated

import sh
import typer

from lup.agent.config import settings
from lup.agent.models import AgentOutput
from lup.agent.prompts import get_system_prompt
from lup.agent.subagents import get_subagents
from lup.agent.tools.example import EXAMPLE_TOOLS
from lup.lib.mcp import LupMcpTool

logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def _print_model_source(
    out: io.StringIO, model: type, label: str, indent: str = "    "
) -> None:
    """Print the Python source of a BaseModel class."""
    out.write(f"\n{indent}{label}:\n")
    try:
        source = inspect_mod.getsource(model)
        for line in source.splitlines():
            out.write(f"{indent}  {line}\n")
    except (OSError, TypeError):
        out.write(f"{indent}  {model.__name__} (source unavailable)\n")


def _tool_location(tool: LupMcpTool) -> str:
    """Get file:line for the tool handler (unwraps decorators)."""
    handler = inspect_mod.unwrap(tool["sdk_tool"].handler)
    try:
        filepath = inspect_mod.getfile(handler)
        filename = os.path.basename(filepath)
        _, lineno = inspect_mod.getsourcelines(handler)
        return f"{filename}:{lineno}"
    except (OSError, TypeError):
        return "?"


def _tool_signature(tool: LupMcpTool) -> str:
    """One-liner: input fields → output model name, file:line."""
    input_model = tool["input_model"]
    parts: list[str] = []
    for name, f in input_model.model_fields.items():
        ann = f.annotation
        type_name = getattr(ann, "__name__", None) if ann is not None else None
        parts.append(f"{name}: {type_name}" if type_name else name)
    fields = ", ".join(parts)
    output_model = tool.get("output_model")
    output_part = f" → {output_model.__name__}" if output_model else ""
    return f"({fields}){output_part}  [{_tool_location(tool)}]"


def _print_tool_compact(out: io.StringIO, tool: LupMcpTool) -> None:
    """Print a single tool as a one-liner."""
    sdk = tool["sdk_tool"]
    out.write(f"    {sdk.name}{_tool_signature(tool)}\n")


def _print_tool_full(out: io.StringIO, tool: LupMcpTool) -> None:
    """Print a single tool with full description and schemas."""
    sdk = tool["sdk_tool"]
    out.write(f"\n  {sdk.name}\n")
    out.write(f"  {'─' * len(sdk.name)}\n")

    desc_lines = sdk.description.split(". ")
    for line in desc_lines:
        line = line.strip()
        if line:
            out.write(f"    {line}.\n")

    _print_model_source(out, tool["input_model"], "Input")

    output_model = tool.get("output_model")
    if output_model is not None:
        _print_model_source(out, output_model, "Output")


def _collect_tools_by_server() -> dict[str, list[LupMcpTool]]:
    """Collect all LupMcpTool instances grouped by server name."""
    return {
        "example": list(EXAMPLE_TOOLS),
    }


def _collect_all_tools() -> list[LupMcpTool]:
    """Collect all LupMcpTool instances from known tool modules."""
    tools: list[LupMcpTool] = []
    for server_tools in _collect_tools_by_server().values():
        tools.extend(server_tools)
    return tools


def _tool_to_dict(t: LupMcpTool) -> dict[str, object]:
    """Serialize a LupMcpTool for JSON output."""
    output_model = t.get("output_model")
    return {
        "name": t["sdk_tool"].name,
        "description": t["sdk_tool"].description,
        "input_schema": t["input_model"].model_json_schema(),
        "output_schema": output_model.model_json_schema() if output_model else None,
    }


def _page_output(text: str) -> None:
    """Write text through a pager (less) if stdout is a tty, otherwise print."""
    if not sys.stdout.isatty():
        sys.stdout.write(text)
        return
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    try:
        tmp.write(text)
        tmp.close()
        less = sh.Command("less")
        less("-R", "-F", "-X", tmp.name, _fg=True)
    except (sh.CommandNotFound, sh.ErrorReturnCode):
        sys.stdout.write(text)
    finally:
        os.unlink(tmp.name)


@app.command("inspect")
def inspect_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Output as machine-readable JSON"),
    ] = False,
    full: Annotated[
        bool,
        typer.Option("--full", help="Show full details (tool schemas, full prompt)"),
    ] = False,
) -> None:
    """Inspect the full agent configuration: tools, schemas, prompt, subagents."""
    tools_by_server = _collect_tools_by_server()
    all_tools = _collect_all_tools()
    subagents = get_subagents()
    prompt = get_system_prompt()

    if as_json:
        data: dict[str, object] = {
            "model": settings.model,
            "max_thinking_tokens": settings.max_thinking_tokens,
            "tools": [_tool_to_dict(t) for t in all_tools],
            "output_schema": AgentOutput.model_json_schema(),
            "subagents": {
                name: {
                    "description": agent.description,
                    "model": agent.model,
                    "tools": agent.tools,
                }
                for name, agent in subagents.items()
            },
            "system_prompt": prompt,
        }
        typer.echo(json.dumps(data, indent=2))
        return

    # --- Pretty-print mode (write to buffer, then page) ---
    out = io.StringIO()

    out.write("=" * 60 + "\n")
    out.write("  Agent Configuration\n")
    out.write("=" * 60 + "\n")

    # Model
    out.write(f"\nModel: {settings.model}\n")
    out.write(f"Max thinking tokens: {settings.max_thinking_tokens}\n")

    # Tools grouped by server
    total_tools = sum(len(ts) for ts in tools_by_server.values())
    out.write(f"\n{'─' * 60}\n")
    out.write(f"  MCP Tools ({total_tools})\n")
    out.write(f"{'─' * 60}\n")
    for server_name, server_tools in tools_by_server.items():
        out.write(f"\n  {server_name} ({len(server_tools)} tools)\n")
        for t in server_tools:
            if full:
                _print_tool_full(out, t)
            else:
                _print_tool_compact(out, t)

    # Agent output schema
    out.write(f"\n{'─' * 60}\n")
    out.write("  Agent Output Schema\n")
    out.write(f"{'─' * 60}\n")
    if full:
        _print_model_source(out, AgentOutput, "AgentOutput", indent="  ")
    else:
        for name, f in AgentOutput.model_fields.items():
            ann = f.annotation
            type_name = getattr(ann, "__name__", None) if ann is not None else None
            out.write(f"    {name}: {type_name or '?'}\n")

    # Subagents
    out.write(f"\n{'─' * 60}\n")
    out.write(f"  Subagents ({len(subagents)})\n")
    out.write(f"{'─' * 60}\n")
    for name, agent in subagents.items():
        out.write(f"\n  {name} (model: {agent.model})\n")
        if full:
            out.write(f"    {agent.description}\n")
        if agent.tools:
            out.write(f"    Tools: {', '.join(agent.tools)}\n")

    # System prompt
    out.write(f"\n{'─' * 60}\n")
    out.write("  System Prompt\n")
    out.write(f"{'─' * 60}\n")
    if full or len(prompt) <= 500:
        out.write(prompt + "\n")
    else:
        out.write(f"{prompt[:500]}... ({len(prompt)} chars total, use --full to see all)\n")

    out.write("\n")

    _page_output(out.getvalue())


# ---------------------------------------------------------------------------
# serve-tools
# ---------------------------------------------------------------------------


def _run_stdio_server() -> None:
    """Run the MCP stdio server with all SDK tools."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool

    from lup.lib.mcp import _generate_json_schema, extract_sdk_tools

    sdk_tools = extract_sdk_tools(_collect_all_tools())
    tool_map = {t.name: t for t in sdk_tools}

    server = Server("lup-tools", version="1.0.0")

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[Tool]:
        tool_list = []
        for t in sdk_tools:
            schema = _generate_json_schema(t.input_schema)
            tool_list.append(
                Tool(name=t.name, description=t.description, inputSchema=schema)
            )
        return tool_list

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str, arguments: dict[str, object]
    ) -> list[dict[str, str]]:
        if name not in tool_map:
            raise ValueError(f"Tool '{name}' not found")
        result = await tool_map[name].handler(arguments)
        return result.get("content", [])  # type: ignore[return-value]

    async def run() -> None:
        init_options = server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, init_options)

    asyncio.run(run())


@app.command("serve-tools")
def serve_tools_cmd() -> None:
    """Start SDK tools as an MCP stdio server.

    This is used by the ``chat`` command — claude CLI launches it as a subprocess.
    Can also be used standalone for testing MCP tool integration.
    """
    _run_stdio_server()


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------


@app.command("chat")
def chat_cmd(
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Override the model (e.g. sonnet, opus)"),
    ] = None,
    no_tools: Annotated[
        bool,
        typer.Option("--no-tools", help="Skip MCP tool server"),
    ] = False,
    no_prompt: Annotated[
        bool,
        typer.Option("--no-prompt", help="Skip appending the agent system prompt"),
    ] = False,
) -> None:
    """Launch an interactive claude session with the agent's tools and prompt.

    Starts the SDK MCP tools as a stdio server, generates the system prompt,
    and execs into ``claude`` with the right flags.
    """
    claude_args: list[str] = []

    # Model
    effective_model = model or settings.model
    claude_args.extend(["--model", effective_model])

    # System prompt
    if not no_prompt:
        prompt = get_system_prompt()
        claude_args.extend(["--append-system-prompt", prompt])

    # MCP config with serve-tools as stdio server
    mcp_config_path: str | None = None
    if not no_tools:
        mcp_config = {
            "mcpServers": {
                "lup-tools": {
                    "command": "uv",
                    "args": ["run", "lup-devtools", "agent", "serve-tools"],
                }
            }
        }
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="lup-mcp-", delete=False
        )
        json.dump(mcp_config, tmp)
        tmp.close()
        mcp_config_path = tmp.name
        claude_args.extend(["--mcp-config", mcp_config_path])

    typer.echo(f"Launching claude with model={effective_model}")
    if not no_tools:
        typer.echo(f"MCP config: {mcp_config_path}")
    if not no_prompt:
        typer.echo("System prompt: appended")

    # exec into claude so the user gets a full interactive session
    try:
        claude = sh.Command("claude")
        claude(*claude_args, _fg=True)
    except sh.CommandNotFound:
        typer.echo("Error: 'claude' CLI not found. Install Claude Code first.", err=True)
        raise typer.Exit(1)
    except sh.ErrorReturnCode:
        pass  # claude exited normally or user quit
    finally:
        if mcp_config_path:
            try:
                os.unlink(mcp_config_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# repl
# ---------------------------------------------------------------------------


_PROMPT = "\033[1;34m❯\033[0m "  # bold blue ❯


async def _repl(
    *,
    model: str | None = None,
    no_tools: bool = False,
    no_prompt: bool = False,
) -> None:
    """Run the interactive REPL loop."""
    from rich.console import Console
    from rich.panel import Panel

    from lup.lib import build_client, ResponseCollector
    from lup.lib.mcp import create_mcp_server, extract_sdk_tools

    console = Console(highlight=False)
    effective_model = model or settings.model

    mcp_servers: dict[str, object] = {}
    if not no_tools:
        example_server = create_mcp_server(
            name="example",
            version="1.0.0",
            tools=extract_sdk_tools(EXAMPLE_TOOLS),
        )
        mcp_servers = {"example": example_server}

    prompt = get_system_prompt() if not no_prompt else ""

    # Welcome panel with server → tool listing
    panel_lines = [
        f"[bold]✻ Agent REPL[/bold]",
        f"[dim]model:[/dim] {effective_model}",
    ]
    if not no_tools:
        servers = _collect_tools_by_server()
        for i, (name, tools) in enumerate(servers.items()):
            is_last_server = i == len(servers) - 1
            panel_lines.append(f"[dim]{'└' if is_last_server else '├'} {name}[/dim]")
            for j, t in enumerate(tools):
                is_last_tool = j == len(tools) - 1
                branch = "  └" if is_last_tool else "  ├"
                if not is_last_server:
                    branch = f"[dim]│[/dim] {'└' if is_last_tool else '├'}"
                panel_lines.append(f"[dim]{branch}[/dim] {t['sdk_tool'].name}")
    else:
        panel_lines.append("[dim]no tools[/dim]")
    panel_lines += ["", "[dim]/quit to exit[/dim]"]

    console.print()
    console.print(Panel("\n".join(panel_lines), border_style="blue", width=60))
    console.print()

    async with build_client(
        model=effective_model,
        system_prompt=prompt,
        max_thinking_tokens=settings.max_thinking_tokens or (128_000 - 1),
        permission_mode="bypassPermissions",
        mcp_servers=mcp_servers if mcp_servers else None,
        agents=get_subagents(),
    ) as client:
        while True:
            try:
                user_input = await asyncio.to_thread(input, _PROMPT)
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            stripped = user_input.strip()
            if not stripped:
                continue
            if stripped in ("/quit", "/exit", "/q"):
                break

            await client.query(user_input)
            collector = ResponseCollector(spaced=True)
            try:
                result = await collector.collect(client)
                parts: list[str] = []
                if result.duration_ms:
                    secs = result.duration_ms / 1000
                    parts.append(f"{secs:.1f}s")
                if result.total_cost_usd:
                    parts.append(f"${result.total_cost_usd:.4f}")
                if parts:
                    console.print(
                        f"  [dim]{' · '.join(parts)}[/dim]"
                    )
                console.print()
            except RuntimeError as e:
                console.print(f"  [red]error:[/red] {e}")
                console.print()
            except KeyboardInterrupt:
                console.print("\n[dim](interrupted)[/dim]")
                await client.interrupt()


@app.command("repl")
def repl_cmd(
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Override the model"),
    ] = None,
    no_tools: Annotated[
        bool,
        typer.Option("--no-tools", help="Skip MCP tools"),
    ] = False,
    no_prompt: Annotated[
        bool,
        typer.Option("--no-prompt", help="Skip agent system prompt"),
    ] = False,
) -> None:
    """Interactive REPL — continuous session with the agent via the SDK."""
    asyncio.run(_repl(model=model, no_tools=no_tools, no_prompt=no_prompt))
