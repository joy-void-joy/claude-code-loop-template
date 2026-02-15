"""Track upstream repos and review commits since last sync.

Mechanical helper for /lup:update. Two config files:

- downstream.json (committed): declares upstream repos with URLs.
  Ships with the lup template GitHub URL by default.
- downstream.json.local (gitignored): local paths, sync state, and overrides.
  Overrides/extends downstream.json entries by project name.
  Set "ignore": true to skip a project (useful when you ARE the upstream).

The script merges both: .local entries override .json entries by name.
Projects with a URL but no local path are auto-cloned to .cache/downstream/.
"""

import json
import logging
from pathlib import Path
from typing import Annotated

import sh
import typer

app = typer.Typer(no_args_is_help=True)
logger = logging.getLogger(__name__)

DOWNSTREAM_FILE = Path("downstream.json")
LOCAL_FILE = Path("downstream.json.local")
CACHE_DIR = Path(".cache/downstream")

_git = sh.Command("git").bake("--no-pager")


def _load_json(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        return {"projects": []}
    result: dict[str, list[dict[str, str]]] = json.loads(path.read_text())
    return result


def _save_local(data: dict[str, list[dict[str, str]]]) -> None:
    LOCAL_FILE.write_text(json.dumps(data, indent=2) + "\n")


def load_projects() -> list[dict[str, str]]:
    """Load and merge projects from downstream.json + downstream.json.local."""
    base = _load_json(DOWNSTREAM_FILE)
    local = _load_json(LOCAL_FILE)

    merged: dict[str, dict[str, str]] = {}
    for p in base.get("projects", []):
        merged[p["name"]] = dict(p)
    for p in local.get("projects", []):
        name = p["name"]
        if name in merged:
            base_entry = merged[name]
            merged[name] = {**base_entry, **p}
        else:
            merged[name] = dict(p)

    return list(merged.values())


def find_project(name: str) -> dict[str, str]:
    """Find a project by name, raising Exit if not found."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == name), None)
    if not proj:
        typer.echo(f"Project '{name}' not found.")
        typer.echo(f"Available: {', '.join(p['name'] for p in projects)}")
        raise typer.Exit(1)
    return proj


def ensure_local(proj: dict[str, str]) -> str:
    """Ensure a project has a usable local path."""
    path = proj.get("path", "")
    if path and Path(path).exists():
        return path

    name = proj["name"]
    cache_path = CACHE_DIR / name
    url = proj.get("url", "")

    if cache_path.exists():
        typer.echo(f"Fetching latest for '{name}' from cache...")
        try:
            _git("-C", str(cache_path), "fetch", "--quiet")
            _git("-C", str(cache_path), "reset", "--hard", "origin/HEAD", "--quiet")
        except sh.ErrorReturnCode as e:
            typer.echo(f"Warning: fetch failed: {e.stderr.decode().strip()}")
        return str(cache_path)

    if url:
        typer.echo(f"Cloning '{name}' from {url}...")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            _git("clone", "--depth=200", url, str(cache_path))
        except sh.ErrorReturnCode as e:
            typer.echo(f"Clone failed: {e.stderr.decode().strip()}")
            raise typer.Exit(1)
        return str(cache_path)

    typer.echo(f"Project '{name}' has no local path or URL configured.")
    typer.echo("\nEither:")
    typer.echo("  1. Add a URL to downstream.json")
    typer.echo(f"  2. Run: uv run lup-devtools sync setup {name} /path/to/repo")
    raise typer.Exit(1)


def git_in(path: str, *args: str) -> str:
    """Run git command in a specific directory."""
    return str(_git("-C", path, *args)).strip()


def commit_count(path: str, since: str) -> int:
    """Count commits since a given ref."""
    if not since:
        output = git_in(path, "rev-list", "--count", "HEAD")
        return int(output)
    output = git_in(path, "rev-list", "--count", f"{since}..HEAD")
    return int(output)


def current_head(path: str) -> str:
    """Get current HEAD sha."""
    return git_in(path, "rev-parse", "HEAD")


def _resolve_path(proj: dict[str, str]) -> tuple[str, bool]:
    """Resolve project to a local path, return (path, exists)."""
    path = proj.get("path", "")
    if path and Path(path).exists():
        return path, True

    cache_path = CACHE_DIR / proj["name"]
    if cache_path.exists():
        return str(cache_path), True

    return proj.get("url", "NO PATH"), False


@app.command("list")
def list_projects_cmd() -> None:
    """Show tracked projects and their sync status."""
    projects = load_projects()

    if not projects:
        typer.echo("No projects tracked. Check downstream.json or run 'setup'.")
        raise typer.Exit(1)

    print(f"\n{'Project':<20} {'Behind':<10} {'Last Synced':<12} {'Source'}")
    print("-" * 80)

    for p in projects:
        if p.get("ignore"):
            print(f"{p['name']:<20} {'—':<10} {'ignored':<12} (skipped)")
            continue

        synced = p.get("last_synced_commit", "")
        synced_short = synced[:8] if synced else "never"

        resolved, exists = _resolve_path(p)
        if not exists:
            print(
                f"{p['name']:<20} {'?':<10} {synced_short:<12} {resolved} (run list after clone)"
            )
            continue

        behind = commit_count(resolved, synced)
        print(f"{p['name']:<20} {behind:<10} {synced_short:<12} {resolved}")

    print()


@app.command("log")
def show_log(
    project: Annotated[str, typer.Argument(help="Project name")],
    stat: Annotated[bool, typer.Option("--stat", help="Show file stats")] = True,
) -> None:
    """Show commits since last sync for a project."""
    proj = find_project(project)
    path = ensure_local(proj)

    synced = proj.get("last_synced_commit", "")
    range_spec = f"{synced}..HEAD" if synced else "HEAD"

    args = ["log", "--oneline"]
    if stat:
        args.append("--stat")
    args.append(range_spec)

    output = git_in(path, *args)
    if output:
        print(output)
    else:
        print(f"No new commits since {synced[:8]}.")


@app.command("diff")
def show_diff(
    project: Annotated[str, typer.Argument(help="Project name")],
    commit: Annotated[str, typer.Argument(help="Commit SHA to show")],
) -> None:
    """Show full diff for a specific commit."""
    proj = find_project(project)
    path = ensure_local(proj)
    output = git_in(path, "show", commit)
    print(output)


@app.command("mark-synced")
def mark_synced(
    project: Annotated[str, typer.Argument(help="Project name")],
) -> None:
    """Update last_synced_commit to the project's current HEAD."""
    proj = find_project(project)
    path = ensure_local(proj)

    head = current_head(path)

    local_data = _load_json(LOCAL_FILE)
    local_projects = local_data.get("projects", [])

    entry = next((p for p in local_projects if p["name"] == project), None)
    if entry:
        entry["last_synced_commit"] = head
    else:
        local_projects.append(
            {
                "name": project,
                "path": path,
                "last_synced_commit": head,
            }
        )
        local_data["projects"] = local_projects

    _save_local(local_data)
    typer.echo(f"Marked '{project}' as synced at {head[:8]}.")


@app.command("setup")
def setup_project(
    name: Annotated[
        str, typer.Argument(help="Project name (must match downstream.json)")
    ],
    path: Annotated[str, typer.Argument(help="Local path to the repo")],
    synced: Annotated[
        bool, typer.Option("--synced", help="Mark as already synced at current HEAD")
    ] = False,
) -> None:
    """Set the local path for a project (writes to downstream.json.local)."""
    resolved = Path(path).resolve()
    if not resolved.exists():
        typer.echo(f"Path does not exist: {resolved}")
        raise typer.Exit(1)

    if not (resolved / ".git").exists() and not (resolved / ".git").is_file():
        typer.echo(f"Not a git repository: {resolved}")
        raise typer.Exit(1)

    local_data = _load_json(LOCAL_FILE)
    local_projects = local_data.get("projects", [])

    entry = next((p for p in local_projects if p["name"] == name), None)
    if entry:
        entry["path"] = str(resolved)
    else:
        entry = {"name": name, "path": str(resolved)}
        local_projects.append(entry)
        local_data["projects"] = local_projects

    if synced:
        entry["last_synced_commit"] = current_head(str(resolved))

    _save_local(local_data)
    typer.echo(f"Set '{name}' local path to {resolved}")
    if synced:
        typer.echo(f"  Marked as synced at {entry['last_synced_commit'][:8]}")
