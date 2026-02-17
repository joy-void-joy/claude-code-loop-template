"""API inspection and module info tools.

Combines inspect_api and module_info into one sub-app.
"""

import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# inspect: Explore Python package APIs
# ---------------------------------------------------------------------------


def _resolve_object(path: str) -> tuple[object, str]:
    """Resolve a dotted path to a Python object."""
    parts = path.split(".")

    for i in range(len(parts), 0, -1):
        module_path = ".".join(parts[:i])
        try:
            obj = importlib.import_module(module_path)
            for attr in parts[i:]:
                obj = getattr(obj, attr)
            return obj, parts[-1]
        except (ImportError, AttributeError):
            continue

    raise ValueError(f"Could not resolve: {path}")


def _format_signature(obj: object, name: str) -> str:
    """Format the signature of a callable."""
    if not callable(obj):
        return name
    try:
        sig = inspect.signature(obj)
        return f"{name}{sig}"
    except (ValueError, TypeError):
        return name


def _get_docstring(obj: object) -> str:
    """Get docstring, handling None."""
    doc = inspect.getdoc(obj)
    return doc if doc else "(no docstring)"


@app.command("inspect")
def inspect_cmd(
    path: Annotated[
        str, typer.Argument(help="Dotted path like module.Class or module.Class.method")
    ],
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
        obj, name = _resolve_object(path)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n{'=' * 60}")
    typer.echo(f"  {path}")
    typer.echo(f"{'=' * 60}\n")

    obj_type = type(obj).__name__
    typer.echo(f"Type: {obj_type}")

    if inspect.ismodule(obj):
        typer.echo(f"\nDocstring:\n{_get_docstring(obj)}\n")

        members = []
        for member_name in dir(obj):
            if member_name.startswith("_") and not private:
                continue
            member = getattr(obj, member_name)
            if inspect.isclass(member):
                members.append(f"  class {member_name}")
            elif inspect.isfunction(member):
                members.append(f"  def {_format_signature(member, member_name)}")
            elif not callable(member):
                members.append(f"  {member_name} = {type(member).__name__}")

        if members:
            typer.echo("Members:")
            for m in sorted(members):
                typer.echo(m)

    elif inspect.isclass(obj):
        typer.echo(f"\nDocstring:\n{_get_docstring(obj)}\n")

        bases = [b.__name__ for b in obj.__bases__ if b is not object]
        if bases:
            typer.echo(f"Bases: {', '.join(bases)}")

        if hasattr(obj, "__init__"):
            init_sig = _format_signature(obj.__init__, "__init__")
            typer.echo(f"\n{init_sig}")
            init_doc = _get_docstring(obj.__init__)
            if init_doc != "(no docstring)":
                typer.echo(f"  {init_doc[:200]}...")

        methods = []
        for member_name, member in inspect.getmembers(obj):
            if member_name.startswith("_") and not private:
                continue

            if not help_full:
                if member_name not in obj.__dict__:
                    continue

            if inspect.isfunction(member) or inspect.ismethod(member):
                sig = _format_signature(member, member_name)
                methods.append(f"  def {sig}")
            elif isinstance(member, property):
                methods.append(f"  @property {member_name}")

        if methods:
            typer.echo("\nMethods:")
            for m in sorted(methods):
                typer.echo(m)

    elif callable(obj):
        sig = _format_signature(obj, name)
        typer.echo(f"\n{sig}")
        typer.echo(f"\nDocstring:\n{_get_docstring(obj)}")

        try:
            source_file = inspect.getfile(obj)
            source_lines = inspect.getsourcelines(obj)
            typer.echo(f"\nSource: {source_file}:{source_lines[1]}")
        except (TypeError, OSError):
            pass

    else:
        typer.echo(f"Value: {repr(obj)[:500]}")
        typer.echo(f"\nDocstring:\n{_get_docstring(obj)}")

    typer.echo("")


# ---------------------------------------------------------------------------
# module-info: Get paths and source code for installed modules
# ---------------------------------------------------------------------------


def _find_module_path(module_name: str) -> Path | None:
    """Find the file path for a module."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            return Path(spec.origin)
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "__file__") and module.__file__:
            return Path(module.__file__)
    except (ImportError, ModuleNotFoundError):
        pass

    return None


@app.command("module-path")
def module_path(
    module: Annotated[
        str, typer.Argument(help="Module name (e.g., 'requests' or 'requests.api')")
    ],
) -> None:
    """Show the file path for a module."""
    path = _find_module_path(module)

    if path is None:
        typer.echo(f"Error: Could not find module '{module}'", err=True)
        raise typer.Exit(1)

    typer.echo(path)

    if path.name == "__init__.py":
        typer.echo(f"Package root: {path.parent}")


@app.command("module-source")
def module_source(
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
    path = _find_module_path(module)

    if path is None:
        typer.echo(f"Error: Could not find module '{module}'", err=True)
        raise typer.Exit(1)

    if not path.exists():
        typer.echo(f"Error: Module file does not exist: {path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"# {path}")
    typer.echo(f"# Lines {start}-{start + lines - 1 if lines > 0 else 'end'}")
    typer.echo("")

    try:
        content = path.read_text()
        source_lines = content.splitlines()

        start_idx = max(0, start - 1)

        if lines > 0:
            end_idx = start_idx + lines
            selected = source_lines[start_idx:end_idx]
        else:
            selected = source_lines[start_idx:]

        for i, line in enumerate(selected, start=start_idx + 1):
            typer.echo(f"{i:4d}  {line}")

    except OSError as e:
        typer.echo(f"Error reading source: {e}", err=True)
        raise typer.Exit(1)


@app.command("module-tree")
def module_tree(
    module: Annotated[str, typer.Argument(help="Package name (e.g., 'requests')")],
) -> None:
    """Show the file tree for a package."""
    path = _find_module_path(module)

    if path is None:
        typer.echo(f"Error: Could not find module '{module}'", err=True)
        raise typer.Exit(1)

    if path.name == "__init__.py":
        package_root = path.parent
    else:
        typer.echo(f"{path}")
        return

    typer.echo(f"{package_root}/")

    py_files = sorted(package_root.rglob("*.py"))
    for py_file in py_files:
        relative = py_file.relative_to(package_root)
        depth = len(relative.parts) - 1
        indent = "  " * depth
        typer.echo(f"{indent}├── {py_file.name}")


@app.command("module-info")
def module_info(module: Annotated[str, typer.Argument(help="Module name")]) -> None:
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
        first_para = doc.split("\n\n")[0]
        typer.echo(f"\nDocstring:\n{first_para[:500]}")

    public_attrs = [a for a in dir(mod) if not a.startswith("_")]
    if public_attrs:
        typer.echo(f"\nPublic API ({len(public_attrs)} items):")
        for attr in sorted(public_attrs)[:30]:
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
