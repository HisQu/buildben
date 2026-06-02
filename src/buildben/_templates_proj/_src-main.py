"""Command-line entrypoint for <my_project>."""

from __future__ import annotations

# == Standard Library ========================
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

# == 3rd Party ===============================
import typer
from apprc.cli import bootstrap_cli_env
from apprc.config.environment import EnvBootstrapResult
from apprc.logging import get_logger, setup_logging

# == Internal ================================
from <my_project>.config import APP_CONFIG

LOG = get_logger(__name__)

app = typer.Typer(
    help="<my_project> command suite.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@dataclass(slots=True)
class CLIState:
    """Top-level CLI state shared with generated config commands."""

    env_file: Path | None
    no_dotenv: bool
    log_level: str
    env_file_overrides_shell: bool = False
    env_bootstrap: EnvBootstrapResult | None = None
    storage: str | None = None


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
    if ctx.resilient_parsing:
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


app.add_typer(
    APP_CONFIG.typer_app(state_type=CLIState),
    name="config",
)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
