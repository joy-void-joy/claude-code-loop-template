"""Root CLI app composing all devtools sub-apps."""

import typer

from lup.devtools.api import app as api_app
from lup.devtools.dev import app as dev_app
from lup.devtools.feedback import app as feedback_app
from lup.devtools.git import app as git_app
from lup.devtools.metrics import app as metrics_app
from lup.devtools.sync import app as sync_app
from lup.devtools.trace import app as trace_app
from lup.devtools.usage import app as usage_app

app = typer.Typer(
    help="lup-devtools: development and analysis tools",
    pretty_exceptions_show_locals=False,
    no_args_is_help=True,
)

app.add_typer(api_app, name="api", help="API inspection and module info")
app.add_typer(dev_app, name="dev", help="Development tools (worktrees)")
app.add_typer(feedback_app, name="feedback", help="Feedback collection")
app.add_typer(git_app, name="git", help="Git operations for sessions")
app.add_typer(metrics_app, name="metrics", help="Aggregate metrics")
app.add_typer(sync_app, name="sync", help="Upstream sync tracking")
app.add_typer(trace_app, name="trace", help="Trace analysis")
app.add_typer(usage_app, name="usage", help="Claude Code usage display")
