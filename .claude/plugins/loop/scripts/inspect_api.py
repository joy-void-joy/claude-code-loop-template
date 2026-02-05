#!/usr/bin/env python3
"""Explore Python package APIs.

Never use `python -c "import ..."` or ad-hoc REPL commands - use this script instead.

Usage:
    uv run python .claude/plugins/loop/scripts/inspect_api.py <module.Class>
    uv run python .claude/plugins/loop/scripts/inspect_api.py <module.Class.method>
    uv run python .claude/plugins/loop/scripts/inspect_api.py <module.Class> --help-full
"""

import importlib
import inspect
from typing import Annotated

import typer

app = typer.Typer(help="Explore Python package APIs")


def resolve_object(path: str) -> tuple[object, str]:
    """Resolve a dotted path to a Python object."""
    parts = path.split(".")

    # Try progressively shorter module paths
    obj = None
    for i in range(len(parts), 0, -1):
        module_path = ".".join(parts[:i])
        try:
            obj = importlib.import_module(module_path)
            # Navigate to remaining attributes
            for attr in parts[i:]:
                obj = getattr(obj, attr)
            return obj, parts[-1]
        except (ImportError, AttributeError):
            continue

    raise ValueError(f"Could not resolve: {path}")


def format_signature(obj: object, name: str) -> str:
    """Format the signature of a callable."""
    try:
        sig = inspect.signature(obj)
        return f"{name}{sig}"
    except (ValueError, TypeError):
        return name


def get_docstring(obj: object) -> str:
    """Get docstring, handling None."""
    doc = inspect.getdoc(obj)
    return doc if doc else "(no docstring)"


@app.command()
def main(
    path: Annotated[str, typer.Argument(help="Dotted path like module.Class or module.Class.method")],
    help_full: Annotated[
        bool,
        typer.Option("--help-full", help="Show full help including inherited methods"),
    ] = False,
    private: Annotated[
        bool,
        typer.Option("--private", "-p", help="Include private methods (_name)"),
    ] = False,
) -> None:
    """Inspect a Python module, class, or method."""
    try:
        obj, name = resolve_object(path)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  {path}")
    typer.echo(f"{'='*60}\n")

    # Show type
    obj_type = type(obj).__name__
    typer.echo(f"Type: {obj_type}")

    # For modules
    if inspect.ismodule(obj):
        typer.echo(f"\nDocstring:\n{get_docstring(obj)}\n")

        # List public members
        members = []
        for member_name in dir(obj):
            if member_name.startswith("_") and not private:
                continue
            member = getattr(obj, member_name)
            if inspect.isclass(member):
                members.append(f"  class {member_name}")
            elif inspect.isfunction(member):
                members.append(f"  def {format_signature(member, member_name)}")
            elif not callable(member):
                members.append(f"  {member_name} = {type(member).__name__}")

        if members:
            typer.echo("Members:")
            for m in sorted(members):
                typer.echo(m)

    # For classes
    elif inspect.isclass(obj):
        typer.echo(f"\nDocstring:\n{get_docstring(obj)}\n")

        # Show bases
        bases = [b.__name__ for b in obj.__bases__ if b is not object]
        if bases:
            typer.echo(f"Bases: {', '.join(bases)}")

        # Show __init__ signature
        if hasattr(obj, "__init__"):
            init_sig = format_signature(obj.__init__, "__init__")
            typer.echo(f"\n{init_sig}")
            init_doc = get_docstring(obj.__init__)
            if init_doc != "(no docstring)":
                typer.echo(f"  {init_doc[:200]}...")

        # List methods
        methods = []
        for member_name, member in inspect.getmembers(obj):
            if member_name.startswith("_") and not private:
                continue

            # Skip inherited unless help_full
            if not help_full:
                if member_name not in obj.__dict__:
                    continue

            if inspect.isfunction(member) or inspect.ismethod(member):
                sig = format_signature(member, member_name)
                methods.append(f"  def {sig}")
            elif isinstance(member, property):
                methods.append(f"  @property {member_name}")

        if methods:
            typer.echo("\nMethods:")
            for m in sorted(methods):
                typer.echo(m)

    # For functions/methods
    elif callable(obj):
        sig = format_signature(obj, name)
        typer.echo(f"\n{sig}")
        typer.echo(f"\nDocstring:\n{get_docstring(obj)}")

        # Show source location if available
        try:
            source_file = inspect.getfile(obj)
            source_lines = inspect.getsourcelines(obj)
            typer.echo(f"\nSource: {source_file}:{source_lines[1]}")
        except (TypeError, OSError):
            pass

    # For other objects
    else:
        typer.echo(f"Value: {repr(obj)[:500]}")
        typer.echo(f"\nDocstring:\n{get_docstring(obj)}")

    typer.echo("")


if __name__ == "__main__":
    app()
