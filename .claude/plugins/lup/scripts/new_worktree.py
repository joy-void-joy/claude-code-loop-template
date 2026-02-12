#!/usr/bin/env python3
"""
Create a new worktree with plugin cache refresh.

This script:
1. Creates a new git worktree branching from the current branch
2. Runs uv sync in the new worktree
3. Refreshes the local plugin cache and installs aib-workflow at project scope

Usage:
    uv run python .claude/scripts/new_worktree.py <worktree-name>

Examples:
    uv run python .claude/scripts/new_worktree.py my-feature
    uv run python .claude/scripts/new_worktree.py fix-bug
"""

import shutil
from pathlib import Path

import sh
import typer

app = typer.Typer(help="Create a new worktree with plugin cache refresh")

PLUGIN_CACHE_DIR = (
    Path.home() / ".claude" / "plugins" / "cache" / "local" / "aib-workflow"
)


def get_tree_dir() -> Path:
    """Get the tree directory that contains worktrees."""
    cwd = Path.cwd().resolve()

    # Check if we're in a worktree (has .git file pointing to worktree dir)
    git_path = cwd / ".git"
    if git_path.exists() and git_path.is_file():
        # We're in a worktree, go up to tree/ directory
        if cwd.parent.name == "tree":
            return cwd.parent

    # Check if we're directly in a tree/ directory
    if cwd.name == "tree":
        return cwd

    # Check if parent is the bare repo and has a tree/ subdirectory
    for parent in cwd.parents:
        tree_dir = parent / "tree"
        if tree_dir.exists() and tree_dir.is_dir():
            return tree_dir

    typer.echo(f"Error: Could not find tree/ directory from {cwd}", err=True)
    raise typer.Exit(1)


GITIGNORED_DATA_DIRS = ["logs"]


@app.command()
def create(
    name: str = typer.Argument(..., help="Name for the new worktree/branch"),
    no_sync: bool = typer.Option(False, "--no-sync", help="Skip running uv sync"),
    no_plugin_refresh: bool = typer.Option(
        False, "--no-plugin-refresh", help="Skip plugin cache refresh and install"
    ),
    copy_data: bool = typer.Option(
        True,
        "--copy-data/--no-copy-data",
        help="Copy gitignored data directories (notes/, logs/) to new worktree",
    ),
) -> None:
    """Create a new worktree with plugin cache refresh."""
    cwd = Path.cwd().resolve()
    tree_dir = get_tree_dir()
    new_worktree_path = tree_dir / name

    if new_worktree_path.exists():
        typer.echo(f"Error: {new_worktree_path} already exists", err=True)
        raise typer.Exit(1)

    git = sh.Command("git")
    uv = sh.Command("uv")

    # Get current branch name
    try:
        current_branch = str(git("branch", "--show-current", _tty_out=False)).strip()
    except sh.ErrorReturnCode:
        typer.echo("Error: Could not determine current branch", err=True)
        raise typer.Exit(1)

    branch_name = name if "/" in name else name

    typer.echo(f"Creating worktree '{name}' from branch '{current_branch}'...")
    typer.echo(f"  Location: {new_worktree_path}")
    typer.echo(f"  New branch: {branch_name}")
    typer.echo()

    # Create the worktree with a new branch
    try:
        git(
            "worktree", "add", str(new_worktree_path), "-b", branch_name, _tty_out=False
        )
        typer.echo("✓ Worktree created")
    except sh.ErrorReturnCode as e:
        typer.echo(f"Error creating worktree: {e.stderr.decode()}", err=True)
        raise typer.Exit(1)

    # Copy .env.local if it exists
    env_local = cwd / ".env.local"
    if env_local.exists():
        shutil.copy2(env_local, new_worktree_path / ".env.local")
        typer.echo("✓ Copied .env.local")

    # Copy gitignored data directories (notes/, logs/)
    if copy_data:
        for dir_name in GITIGNORED_DATA_DIRS:
            source_dir = cwd / dir_name
            target_dir = new_worktree_path / dir_name
            if source_dir.exists() and source_dir.is_dir():
                shutil.copytree(source_dir, target_dir)
                typer.echo(f"✓ Copied {dir_name}/")

    # Run uv sync in the new worktree
    if not no_sync:
        typer.echo("Running uv sync...")
        try:
            uv(
                "sync",
                "--all-groups",
                "--all-extras",
                _cwd=str(new_worktree_path),
                _tty_out=False,
            )
            typer.echo("✓ Dependencies synced")
        except sh.ErrorReturnCode as e:
            typer.echo(f"Warning: uv sync failed: {e.stderr.decode()}", err=True)

    # Refresh plugin cache and install at project scope
    if not no_plugin_refresh:
        if PLUGIN_CACHE_DIR.exists():
            shutil.rmtree(PLUGIN_CACHE_DIR)
            typer.echo("✓ Cleared plugin cache (aib-workflow)")

        claude = sh.Command("claude")
        try:
            claude(
                "plugin",
                "install",
                "aib-workflow@local",
                "--scope",
                "project",
                _cwd=str(new_worktree_path),
                _tty_out=False,
            )
            typer.echo("✓ Installed aib-workflow plugin (project scope)")
        except sh.ErrorReturnCode as e:
            typer.echo(f"Warning: plugin install failed: {e.stderr.decode()}", err=True)

    typer.echo()
    cd_command = f"cd /; cd {new_worktree_path}; claude"

    # Try to copy to clipboard
    try:
        xclip = sh.Command("xclip")
        xclip("-selection", "clipboard", _in=cd_command)
        typer.echo(f"Done! Copied to clipboard: {cd_command}")
    except (sh.CommandNotFound, sh.ErrorReturnCode):
        typer.echo("Done! To switch to the new worktree:")
        typer.echo(f"  {cd_command}")


if __name__ == "__main__":
    app()
