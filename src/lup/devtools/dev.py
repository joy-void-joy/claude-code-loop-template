"""Development tools: worktree management."""

import shutil
from pathlib import Path
from typing import Annotated

import sh
import typer

app = typer.Typer(no_args_is_help=True)

git = sh.Command("git")
uv = sh.Command("uv")
xclip = sh.Command("xclip")
xsel = sh.Command("xsel")

PLUGIN_CACHE_DIR = Path.home() / ".claude" / "plugins" / "cache" / "local" / "lup"

GITIGNORED_EXTRAS = [
    ".env.local",
    "downstream.json.local",
    ".claude/settings.local.json",
    "logs",
    "refs",
]


def branch_exists(branch: str) -> bool:
    """Check if a git branch exists (local only)."""
    try:
        git("rev-parse", "--verify", f"refs/heads/{branch}")
        return True
    except sh.ErrorReturnCode:
        return False


def worktree_is_registered(path: Path) -> bool:
    """Check if a path is registered as a git worktree (even if dir is missing)."""
    output = str(git("worktree", "list", "--porcelain"))
    resolved = str(path.resolve())
    for line in output.splitlines():
        if line.startswith("worktree ") and line.split(" ", 1)[1] == resolved:
            return True
    return False


def get_tree_dir() -> Path:
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
        typer.Option("--no-copy-data", help="Skip copying gitignored extras"),
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
    """Create or re-attach a git worktree.

    If the branch already exists, re-attaches it to a worktree directory.
    If the branch doesn't exist, creates a new branch and worktree.
    """
    current_dir = Path.cwd()

    branch_name = name
    worktree_name = name

    tree_dir = get_tree_dir()
    worktree_path = tree_dir / worktree_name
    branch_already_exists = branch_exists(branch_name)

    # Handle existing worktree directory
    if worktree_path.exists():
        if worktree_is_registered(worktree_path):
            typer.echo(f"Worktree already active: {worktree_path}")
            raise typer.Exit(0)
        # Stale directory (worktree was pruned but dir remains) — clean up
        typer.echo(f"Removing stale worktree directory: {worktree_path}")
        shutil.rmtree(worktree_path)

    # Prune stale worktree entries so git doesn't complain
    git("worktree", "prune")

    if branch_already_exists:
        typer.echo(f"Re-attaching worktree: {worktree_path}")
        typer.echo(f"Existing branch: {branch_name}")
    else:
        typer.echo(f"Creating worktree: {worktree_path}")
        typer.echo(f"New branch: {branch_name}")

    try:
        if branch_already_exists:
            git("worktree", "add", str(worktree_path), branch_name)
        elif base_branch:
            git("worktree", "add", str(worktree_path), "-b", branch_name, base_branch)
        else:
            git("worktree", "add", str(worktree_path), "-b", branch_name)
    except sh.ErrorReturnCode as e:
        typer.echo(f"Error creating worktree: {e.stderr.decode()}")
        raise typer.Exit(1)

    if not no_copy_data:
        for rel_path in GITIGNORED_EXTRAS:
            src = current_dir / rel_path
            if not src.exists():
                continue
            dst = worktree_path / rel_path
            if src.is_dir():
                shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
                typer.echo(f"Copied {rel_path}/")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                typer.echo(f"Copied {rel_path}")

    if not no_sync:
        typer.echo("Running uv sync...")
        try:
            uv("sync", _cwd=str(worktree_path))
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
        xclip("-selection", "clipboard", _in=cd_command)
        typer.echo(f"Copied to clipboard: {cd_command}")
    except (sh.ErrorReturnCode, sh.CommandNotFound):
        try:
            xsel("--clipboard", "--input", _in=cd_command)
            typer.echo(f"Copied to clipboard: {cd_command}")
        except (sh.ErrorReturnCode, sh.CommandNotFound):
            typer.echo("Done! To switch to the new worktree:")
            typer.echo(f"  {cd_command}")
