#!/usr/bin/env python3
"""Get paths and source code for installed Python modules.

Usage:
    uv run python .claude/plugins/loop/scripts/module_info.py path <module>
    uv run python .claude/plugins/loop/scripts/module_info.py source <module> [--lines N]
"""

import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Get info about installed Python modules")


def find_module_path(module_name: str) -> Path | None:
    """Find the file path for a module."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            return Path(spec.origin)
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    # Try importing directly
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "__file__") and module.__file__:
            return Path(module.__file__)
    except (ImportError, ModuleNotFoundError):
        pass

    return None


@app.command()
def path(
    module: Annotated[str, typer.Argument(help="Module name (e.g., 'requests' or 'requests.api')")]
) -> None:
    """Show the file path for a module."""
    module_path = find_module_path(module)

    if module_path is None:
        typer.echo(f"Error: Could not find module '{module}'", err=True)
        raise typer.Exit(1)

    typer.echo(module_path)

    # If it's a package (directory), also show the package root
    if module_path.name == "__init__.py":
        typer.echo(f"Package root: {module_path.parent}")


@app.command()
def source(
    module: Annotated[str, typer.Argument(help="Module name (e.g., 'requests.api')")],
    lines: Annotated[
        int,
        typer.Option("--lines", "-n", help="Number of lines to show (0 for all)"),
    ] = 50,
    start: Annotated[
        int,
        typer.Option("--start", "-s", help="Starting line number"),
    ] = 1,
) -> None:
    """Show source code for a module."""
    module_path = find_module_path(module)

    if module_path is None:
        typer.echo(f"Error: Could not find module '{module}'", err=True)
        raise typer.Exit(1)

    if not module_path.exists():
        typer.echo(f"Error: Module file does not exist: {module_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"# {module_path}")
    typer.echo(f"# Lines {start}-{start + lines - 1 if lines > 0 else 'end'}")
    typer.echo("")

    try:
        content = module_path.read_text()
        source_lines = content.splitlines()

        # Adjust for 0-indexing
        start_idx = max(0, start - 1)

        if lines > 0:
            end_idx = start_idx + lines
            selected = source_lines[start_idx:end_idx]
        else:
            selected = source_lines[start_idx:]

        for i, line in enumerate(selected, start=start_idx + 1):
            typer.echo(f"{i:4d}  {line}")

    except Exception as e:
        typer.echo(f"Error reading source: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def tree(
    module: Annotated[str, typer.Argument(help="Package name (e.g., 'requests')")]
) -> None:
    """Show the file tree for a package."""
    module_path = find_module_path(module)

    if module_path is None:
        typer.echo(f"Error: Could not find module '{module}'", err=True)
        raise typer.Exit(1)

    # Get package root
    if module_path.name == "__init__.py":
        package_root = module_path.parent
    else:
        # Single-file module
        typer.echo(f"{module_path}")
        return

    typer.echo(f"{package_root}/")

    # List Python files
    py_files = sorted(package_root.rglob("*.py"))
    for py_file in py_files:
        relative = py_file.relative_to(package_root)
        depth = len(relative.parts) - 1
        indent = "  " * depth
        typer.echo(f"{indent}├── {py_file.name}")


@app.command()
def info(
    module: Annotated[str, typer.Argument(help="Module name")]
) -> None:
    """Show detailed info about a module."""
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        typer.echo(f"Error: Could not import '{module}': {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Module: {module}")

    if hasattr(mod, "__file__"):
        typer.echo(f"File: {mod.__file__}")

    if hasattr(mod, "__version__"):
        typer.echo(f"Version: {mod.__version__}")

    if hasattr(mod, "__doc__") and mod.__doc__:
        doc = mod.__doc__.strip()
        # Show first paragraph
        first_para = doc.split("\n\n")[0]
        typer.echo(f"\nDocstring:\n{first_para[:500]}")

    # Show public API
    public_attrs = [a for a in dir(mod) if not a.startswith("_")]
    if public_attrs:
        typer.echo(f"\nPublic API ({len(public_attrs)} items):")
        for attr in sorted(public_attrs)[:30]:  # Limit output
            obj = getattr(mod, attr)
            obj_type = type(obj).__name__
            if inspect.isclass(obj):
                obj_type = "class"
            elif inspect.isfunction(obj):
                obj_type = "function"
            elif inspect.ismodule(obj):
                obj_type = "module"
            typer.echo(f"  {attr}: {obj_type}")

        if len(public_attrs) > 30:
            typer.echo(f"  ... and {len(public_attrs) - 30} more")


if __name__ == "__main__":
    app()
