"""Typer command tree for <my_project>."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Annotated, Any

import typer
from apprc.cli.bootstrap import bootstrap_cli_env
from apprc.cli.config.state import config_request_skips_runtime_bootstrap
from apprc.cli.typer_utils import dump_json
from apprc.logging import get_logger, setup_logging
from apprc.runtime_config.bootstrap.result import EnvBootstrapResult

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

    :param env_files: Optional dotenv files passed through ``--env-file``.
    :param skip_dotenv_layers: Whether AppRC skipped dotenv layer merging.
    :param log_level: Logging level token used for this process.
    :param env_file_overrides_os_environ: Whether explicit dotenv values beat
        the shell inside this process.
    :param env_bootstrap: AppRC bootstrap summary after startup.
    :param storage: Optional storage selector.
    """

    env_files: tuple[Path, ...]
    skip_dotenv_layers: bool
    log_level: str | None
    env_file_overrides_os_environ: bool = False
    env_bootstrap: EnvBootstrapResult | None = None
    storage: str | None = None


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

    return config_request_skips_runtime_bootstrap("config")


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
    apprc_toml_path = APP_CONFIG.spec.optional_apprc_toml_path()
    return {
        "apprc_toml_env_key": APP_CONFIG.spec.apprc_toml_env_key,
        "apprc_toml_path": str(apprc_toml_path) if apprc_toml_path else None,
        "cwd": str(Path.cwd()),
        "package": PACKAGE_NAME,
        "package_file": str(Path(<my_project>.__file__).resolve()),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "storage_env_key": APP_CONFIG.spec.storage_env_key,
        "version": _package_version(),
    }


def _config_show_payload(state: CLIState) -> dict[str, Any]:
    """Build a small resolved-runtime payload for ``config show``.

    :param state: Root CLI state created by :func:`app_callback`.
    :return: JSON-friendly package and AppRC bootstrap metadata.
    """
    env_bootstrap = state.env_bootstrap
    return {
        "apprc_toml_env_key": APP_CONFIG.spec.apprc_toml_env_key,
        "apprc_toml_path": (
            None
            if env_bootstrap is None or env_bootstrap.apprc_toml_path is None
            else str(env_bootstrap.apprc_toml_path)
        ),
        "env_files": (
            [str(path) for path in state.env_files]
            if env_bootstrap is None
            else [str(path) for path in env_bootstrap.env_files]
        ),
        "log_level": state.log_level,
        "package": PACKAGE_NAME,
        "skip_dotenv_layers": state.skip_dotenv_layers,
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
        "storage_count": 0
        if env_bootstrap is None
        else env_bootstrap.storage_count,
        "storage_env_key": APP_CONFIG.spec.storage_env_key,
        "storage_name": None
        if env_bootstrap is None
        else env_bootstrap.storage_name,
        "storage_root": (
            None
            if env_bootstrap is None or env_bootstrap.storage_root is None
            else str(env_bootstrap.storage_root)
        ),
        "storage_selector_source": (
            None
            if env_bootstrap is None
            else env_bootstrap.storage_selector_source
        ),
        "storage_selector_value": (
            None
            if env_bootstrap is None
            else env_bootstrap.storage_selector_value
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
    env_files: Annotated[
        list[Path] | None,
        typer.Option(
            "--env-file",
            help=(
                "Invocation-local dotenv file loaded after shared/local env. "
                "May be repeated."
            ),
        ),
    ] = None,
    env_file_overrides_os_environ: Annotated[
        bool,
        typer.Option(
            "--env-file-overrides-os-environ",
            "-o",
            help="Let --env-file values override existing process env values.",
        ),
    ] = False,
    skip_dotenv_layers: Annotated[
        bool,
        typer.Option(
            "--skip-dotenv-layers",
            "-s",
            help="Select storage but do not merge dotenv values into env.",
        ),
    ] = False,
    storage: Annotated[
        str | None,
        typer.Option("--storage", help="Storage path or registered selector."),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option("--log-level", help="Logging level name or number."),
    ] = "INFO",
) -> None:
    """Prepare logging and config state before command handlers run."""
    state = CLIState(
        env_files=tuple(env_files or ()),
        skip_dotenv_layers=skip_dotenv_layers,
        log_level=log_level,
        env_file_overrides_os_environ=env_file_overrides_os_environ,
        storage=storage,
    )
    ctx.obj = state
    if (
        ctx.resilient_parsing
        or "--help" in sys.argv[1:]
        or _request_skips_bootstrap(ctx)
    ):
        return
    state.env_bootstrap = bootstrap_cli_env(
        APP_CONFIG,
        env_files=state.env_files,
        env_file_overrides_os_environ=env_file_overrides_os_environ,
        load_dotenv_layers=not skip_dotenv_layers,
        storage=storage,
        log_level=log_level,
        setup_logging=setup_logging,
        logger=LOG,
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
