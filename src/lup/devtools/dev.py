"""Development tools: worktree management."""

import shutil
from pathlib import Path
from typing import Annotated

import sh
import typer

app = typer.Typer(no_args_is_help=True)

_git = sh.Command("git").bake()
_uv = sh.Command("uv").bake()
_xclip = sh.Command("xclip")
_xsel = sh.Command("xsel")

PLUGIN_CACHE_DIR = Path.home() / ".claude" / "plugins" / "cache" / "local" / "lup"

GITIGNORED_DATA_DIRS = ["logs"]


def _get_tree_dir() -> Path:
    """Find the tree/ directory that contains worktrees.

    Walks up from cwd looking for a tree/ directory that is a sibling
    of a bare git repo or worktree root.
    """
    cwd = Path.cwd().resolve()

    if cwd.parent.name == "tree":
        return cwd.parent

    tree = cwd / "tree"
    if tree.is_dir():
        return tree

    for parent in cwd.parents:
        tree = parent / "tree"
        if tree.is_dir():
            return tree

    typer.echo("Error: Could not find tree/ directory", err=True)
    raise typer.Exit(1)


@app.command("worktree")
def worktree_cmd(
    name: Annotated[
        str, typer.Argument(help="Name for the worktree (e.g., feat-name)")
    ],
    no_sync: Annotated[
        bool,
        typer.Option("--no-sync", help="Skip running uv sync"),
    ] = False,
    no_copy_data: Annotated[
        bool,
        typer.Option("--no-copy-data", help="Skip copying .env.local and logs/"),
    ] = False,
    no_plugin_refresh: Annotated[
        bool,
        typer.Option(
            "--no-plugin-refresh", help="Skip plugin cache refresh and install"
        ),
    ] = False,
    base_branch: Annotated[
        str | None,
        typer.Option("--base", "-b", help="Base branch (default: current branch)"),
    ] = None,
) -> None:
    """Create a new git worktree with plugin cache refresh."""
    current_dir = Path.cwd()

    branch_name = f"feat/{name}" if not name.startswith("feat/") else name
    worktree_name = name.replace("feat/", "")

    tree_dir = _get_tree_dir()
    worktree_path = tree_dir / worktree_name
    if worktree_path.exists():
        typer.echo(f"Error: Worktree path already exists: {worktree_path}")
        raise typer.Exit(1)

    typer.echo(f"Creating worktree: {worktree_path}")
    typer.echo(f"Branch: {branch_name}")

    try:
        if base_branch:
            _git("worktree", "add", str(worktree_path), "-b", branch_name, base_branch)
        else:
            _git("worktree", "add", str(worktree_path), "-b", branch_name)
    except sh.ErrorReturnCode as e:
        typer.echo(f"Error creating worktree: {e.stderr.decode()}")
        raise typer.Exit(1)

    if not no_copy_data:
        env_local = current_dir / ".env.local"
        if env_local.exists():
            shutil.copy2(env_local, worktree_path / ".env.local")
            typer.echo("Copied .env.local")

        for data_dir_name in GITIGNORED_DATA_DIRS:
            data_dir = current_dir / data_dir_name
            if data_dir.exists():
                shutil.copytree(
                    data_dir, worktree_path / data_dir_name, dirs_exist_ok=True
                )
                typer.echo(f"Copied {data_dir_name}/")

    if not no_sync:
        typer.echo("Running uv sync...")
        try:
            _uv("sync", _cwd=str(worktree_path))
        except sh.ErrorReturnCode as e:
            typer.echo(f"Warning: uv sync failed: {e.stderr.decode()}")

    if not no_plugin_refresh:
        if PLUGIN_CACHE_DIR.exists():
            shutil.rmtree(PLUGIN_CACHE_DIR)
            typer.echo("Cleared plugin cache (lup)")

        claude = sh.Command("claude")
        try:
            claude(
                "plugin",
                "install",
                "lup@local",
                "--scope",
                "project",
                _cwd=str(worktree_path),
                _tty_out=False,
            )
            typer.echo("Installed lup plugin (project scope)")
        except sh.ErrorReturnCode as e:
            typer.echo(f"Warning: plugin install failed: {e.stderr.decode()}", err=True)

    typer.echo()
    cd_command = f"cd /; cd {worktree_path}; claude"

    try:
        _xclip("-selection", "clipboard", _in=cd_command)
        typer.echo(f"Copied to clipboard: {cd_command}")
    except (sh.ErrorReturnCode, sh.CommandNotFound):
        try:
            _xsel("--clipboard", "--input", _in=cd_command)
            typer.echo(f"Copied to clipboard: {cd_command}")
        except (sh.ErrorReturnCode, sh.CommandNotFound):
            typer.echo("Done! To switch to the new worktree:")
            typer.echo(f"  {cd_command}")
