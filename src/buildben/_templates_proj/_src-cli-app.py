"""Typer command tree for <my_project>."""

from __future__ import annotations

import json
import sys
from importlib import metadata
from pathlib import Path
from typing import Annotated, Any

import typer

import <my_project>

PACKAGE_NAME = "<my_project>"
VERSION_FALLBACK = "0.1.0"

app = typer.Typer(
    add_completion=True,
    help="Command-line tools for <my_project>.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


def _package_version() -> str:
    """Return the installed package version.

    :return: Installed package metadata version, or the scaffold fallback when
        running from ``PYTHONPATH`` before installation.
    """
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return VERSION_FALLBACK


def _diagnose_payload() -> dict[str, Any]:
    """Build a stable diagnostic payload for support reports.

    :return: JSON-friendly process, package, and import metadata.
    """
    return {
        "cwd": str(Path.cwd()),
        "package": PACKAGE_NAME,
        "package_file": str(Path(<my_project>.__file__).resolve()),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "version": _package_version(),
    }


def _echo_diagnose_payload(payload: dict[str, Any]) -> None:
    """Print a human-readable diagnostic payload.

    :param payload: Diagnostic values returned by :func:`_diagnose_payload`.
    :return: None.
    """
    for key in sorted(payload):
        typer.echo(f"{key}: {payload[key]}")


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(_package_version())


@app.command("diagnose")
def diagnose_cmd(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Print local package and Python diagnostics."""
    payload = _diagnose_payload()
    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    _echo_diagnose_payload(payload)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
