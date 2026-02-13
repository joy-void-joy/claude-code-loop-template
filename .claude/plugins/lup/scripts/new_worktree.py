#!/usr/bin/env python3
"""Create a new git worktree with Claude session migration.

This script:
1. Creates a new worktree from the current branch
2. Copies .env.local and logs/ to the new worktree
3. Runs uv sync in the new worktree
4. Migrates the current Claude session to the new worktree

Usage:
    uv run python .claude/plugins/lup/scripts/new_worktree.py <name>
    uv run python .claude/plugins/lup/scripts/new_worktree.py <name> --session-id <uuid>
    uv run python .claude/plugins/lup/scripts/new_worktree.py <name> --no-sync
"""

import shutil
from pathlib import Path
from typing import Annotated

import sh
import typer

app = typer.Typer(help="Create git worktrees with Claude session migration")


def get_claude_session_dir() -> Path:
    """Get the Claude projects directory."""
    return Path.home() / ".claude" / "projects"


def find_current_session(project_path: Path) -> tuple[Path, str] | None:
    """Find the current Claude session for this project."""
    session_dir = get_claude_session_dir()
    if not session_dir.exists():
        return None

    # Claude uses a mangled path as the project identifier
    # e.g., -home-user-project becomes the folder name
    project_str = str(project_path.resolve())
    mangled = project_str.replace("/", "-")
    if mangled.startswith("-"):
        mangled = mangled[1:]

    project_session_dir = session_dir / mangled
    if not project_session_dir.exists():
        return None

    # Find the most recent session file
    session_files = list(project_session_dir.glob("*.jsonl"))
    if not session_files:
        return None

    latest = max(session_files, key=lambda f: f.stat().st_mtime)
    session_id = latest.stem

    return project_session_dir, session_id


def migrate_session(
    old_project: Path,
    new_project: Path,
    session_id: str | None = None,
) -> str | None:
    """Migrate a Claude session to a new project path."""
    session_info = find_current_session(old_project)
    if not session_info:
        return None

    old_session_dir, current_session_id = session_info
    session_id = session_id or current_session_id

    session_file = old_session_dir / f"{session_id}.jsonl"
    if not session_file.exists():
        return None

    # Create new session directory
    new_project_str = str(new_project.resolve())
    new_mangled = new_project_str.replace("/", "-")
    if new_mangled.startswith("-"):
        new_mangled = new_mangled[1:]

    new_session_dir = get_claude_session_dir() / new_mangled
    new_session_dir.mkdir(parents=True, exist_ok=True)

    # Copy session file
    new_session_file = new_session_dir / f"{session_id}.jsonl"
    shutil.copy2(session_file, new_session_file)

    return session_id


@app.command()
def main(
    name: Annotated[
        str, typer.Argument(help="Name for the worktree (e.g., feat-name)")
    ],
    session_id: Annotated[
        str | None,
        typer.Option("--session-id", "-s", help="Specific session ID to migrate"),
    ] = None,
    no_sync: Annotated[
        bool,
        typer.Option("--no-sync", help="Skip running uv sync"),
    ] = False,
    no_copy_data: Annotated[
        bool,
        typer.Option("--no-copy-data", help="Skip copying .env.local and logs/"),
    ] = False,
    base_branch: Annotated[
        str | None,
        typer.Option("--base", "-b", help="Base branch (default: current branch)"),
    ] = None,
) -> None:
    """Create a new git worktree with Claude session migration."""
    current_dir = Path.cwd()

    # Determine branch name
    branch_name = f"feat/{name}" if not name.startswith("feat/") else name
    worktree_name = name.replace("feat/", "")

    # Worktree path - use tree/ directory
    worktree_path = current_dir.parent / "tree" / worktree_name
    if worktree_path.exists():
        typer.echo(f"Error: Worktree path already exists: {worktree_path}")
        raise typer.Exit(1)

    typer.echo(f"Creating worktree: {worktree_path}")
    typer.echo(f"Branch: {branch_name}")

    # Create worktree
    try:
        if base_branch:
            sh.git(
                "worktree", "add", str(worktree_path), "-b", branch_name, base_branch
            )
        else:
            sh.git("worktree", "add", str(worktree_path), "-b", branch_name)
    except sh.ErrorReturnCode as e:
        typer.echo(f"Error creating worktree: {e.stderr.decode()}")
        raise typer.Exit(1)

    # Copy data files
    if not no_copy_data:
        env_local = current_dir / ".env.local"
        if env_local.exists():
            shutil.copy2(env_local, worktree_path / ".env.local")
            typer.echo("Copied .env.local")

        logs_dir = current_dir / "logs"
        if logs_dir.exists():
            shutil.copytree(logs_dir, worktree_path / "logs", dirs_exist_ok=True)
            typer.echo("Copied logs/")

    # Run uv sync
    if not no_sync:
        typer.echo("Running uv sync...")
        try:
            sh.uv("sync", _cwd=str(worktree_path))
        except sh.ErrorReturnCode as e:
            typer.echo(f"Warning: uv sync failed: {e.stderr.decode()}")

    # Migrate Claude session
    migrated_id = migrate_session(current_dir, worktree_path, session_id)
    if migrated_id:
        typer.echo(f"Migrated Claude session: {migrated_id}")
    else:
        typer.echo("No Claude session found to migrate")

    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("Worktree created successfully!")
    typer.echo("=" * 60)
    typer.echo("\nTo use the new worktree:")
    typer.echo(f"  cd {worktree_path}")
    if migrated_id:
        typer.echo("  claude --resume")
    else:
        typer.echo("  claude")


if __name__ == "__main__":
    app()
