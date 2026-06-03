"""Typer command tree for <my_project>."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Annotated, Any

import typer
from apprc.cli import (
    COMMON_ROOT_VALUE_OPTIONS,
    args_after_command,
    bootstrap_cli_env,
    config_request_skips_bootstrap,
    dump_json,
)
from apprc.config.environment import EnvBootstrapResult
from apprc.logging import get_logger, setup_logging

import <my_project>
from <my_project>.config import APP_CONFIG

PACKAGE_NAME = "<my_project>"
VERSION_FALLBACK = "0.1.0"
LOG = get_logger(__name__)

app = typer.Typer(
    add_completion=True,
    help="Command-line tools for <my_project>.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@dataclass(slots=True)
class CLIState:
    """Root command state shared with AppRC's generated config commands.

    :param env_file: Optional dotenv file passed through ``--env-file``.
    :param no_dotenv: Whether AppRC skipped packaged and local dotenv layers.
    :param log_level: Logging level token used for this process.
    :param env_file_overrides_shell: Whether explicit dotenv values beat the shell.
    :param env_bootstrap: AppRC bootstrap summary after startup.
    :param storage: Optional named storage selected from the AppRC registry.
    """

    env_file: Path | None
    no_dotenv: bool
    log_level: str
    env_file_overrides_shell: bool = False
    env_bootstrap: EnvBootstrapResult | None = None
    storage: str | None = None


def _config_child_args() -> list[str] | None:
    """Return arguments passed after the top-level ``config`` command.

    :return: Child tokens, or ``None`` when the active command is not
        ``config``.
    """
    return args_after_command(
        "config",
        root_value_options=COMMON_ROOT_VALUE_OPTIONS,
    )


def _request_skips_bootstrap(ctx: typer.Context) -> bool:
    """Return whether this invocation can run without AppRC env bootstrap.

    :param ctx: Active Typer callback context.
    :return: Whether the command needs only package metadata or registry-only
        AppRC operations.
    """
    command_name = ctx.invoked_subcommand
    if command_name in {"version", "diagnose"}:
        return True
    if command_name != "config":
        return False

    config_args = _config_child_args()
    if config_args is None:
        return False
    return config_request_skips_bootstrap(config_args)


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
        "registry_path": str(APP_CONFIG.registry_path()),
        "version": _package_version(),
    }


def _config_show_payload(state: CLIState) -> dict[str, Any]:
    """Build a small resolved-runtime payload for ``config show``.

    :param state: Root CLI state created by :func:`app_callback`.
    :return: JSON-friendly package and AppRC bootstrap metadata.
    """
    env_bootstrap = state.env_bootstrap
    return {
        "env_file": str(state.env_file) if state.env_file is not None else None,
        "log_level": state.log_level,
        "no_dotenv": state.no_dotenv,
        "package": PACKAGE_NAME,
        "registry_path": str(APP_CONFIG.registry_path()),
        "shared_env": (
            None
            if env_bootstrap is None or env_bootstrap.shared_env is None
            else str(env_bootstrap.shared_env)
        ),
        "local_env": (
            None
            if env_bootstrap is None or env_bootstrap.local_env is None
            else str(env_bootstrap.local_env)
        ),
        "storage": state.storage,
        "storage_root": (
            None
            if env_bootstrap is None or env_bootstrap.storage_root is None
            else str(env_bootstrap.storage_root)
        ),
        "version": _package_version(),
    }


def _echo_diagnose_payload(payload: dict[str, Any]) -> None:
    """Print a human-readable diagnostic payload.

    :param payload: Diagnostic values returned by :func:`_diagnose_payload`.
    :return: None.
    """
    for key in sorted(payload):
        typer.echo(f"{key}: {payload[key]}")


@app.callback()
def app_callback(
    ctx: typer.Context,
    env_file: Annotated[
        Path | None,
        typer.Option("--env-file", help="Load an additional dotenv file."),
    ] = None,
    env_file_overrides_shell: Annotated[
        bool,
        typer.Option(
            "--env-file-overrides-shell",
            help="Let --env-file beat already exported shell variables.",
        ),
    ] = False,
    no_dotenv: Annotated[
        bool,
        typer.Option("--no-dotenv", help="Skip packaged and local dotenv files."),
    ] = False,
    storage: Annotated[
        str | None,
        typer.Option("--storage", help="Named storage from the AppRC registry."),
    ] = None,
    log_level: Annotated[
        str,
        typer.Option("--log-level", help="Logging level name or number."),
    ] = "INFO",
) -> None:
    """Prepare logging and config state before command handlers run."""
    if (
        ctx.resilient_parsing
        or "--help" in sys.argv[1:]
        or _request_skips_bootstrap(ctx)
    ):
        return
    env_bootstrap = bootstrap_cli_env(
        APP_CONFIG,
        env_file=env_file,
        env_file_overrides_shell=env_file_overrides_shell,
        no_dotenv=no_dotenv,
        storage_name=storage,
        log_level=log_level,
        setup_logging=setup_logging,
        logger=LOG,
    )
    ctx.obj = CLIState(
        env_file=env_file,
        no_dotenv=no_dotenv,
        log_level=log_level,
        env_file_overrides_shell=env_file_overrides_shell,
        env_bootstrap=env_bootstrap,
        storage=storage,
    )


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
        dump_json(payload)
        return
    _echo_diagnose_payload(payload)


app.add_typer(
    APP_CONFIG.typer_app(
        state_type=CLIState,
        runtime_payload=_config_show_payload,
    ),
    name="config",
)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
