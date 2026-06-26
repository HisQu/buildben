"""<my_project>-bound AppRC configuration adapter."""

from __future__ import annotations

# == Standard Library ========================
from collections.abc import Sequence
from pathlib import Path

# == 3rd Party ===============================
from apprc.logging import get_logger
from apprc.runtime_config.bootstrap.result import EnvBootstrapResult
from apprc.runtime_config.kit import AppConfigKit

# == Internal ================================
from <my_project>.config.owners import APP_CONFIG_ENVS

LOG = get_logger(__name__)

APP_CONFIG = AppConfigKit(
    app_name="<my_project>",
    display_name="<my_project>",
    config_package="<my_project>.config",
    envs=APP_CONFIG_ENVS,
    storage_env_key="<MY_PROJECT>_STORAGE",
    command_name="<my_project>",
    apprc_toml_filename="<my_project>.apprc.toml",
    shared_env_filename=".env.shared",
    local_env_filename=".env.local",
)
APP_CONFIG_SPEC = APP_CONFIG.spec


def bootstrap_app_env(
    *,
    env_files: Sequence[Path] = (),
    env_file_overrides_os_environ: bool = False,
    load_dotenv_layers: bool = True,
    storage: str | None = None,
) -> EnvBootstrapResult:
    """Populate ``os.environ`` for one <my_project> CLI process.

    :param env_files: Optional explicit dotenv files.
    :param env_file_overrides_os_environ: Whether explicit dotenv files beat
        exported shell variables inside this process.
    :param load_dotenv_layers: Whether packaged and local dotenv files load.
    :param storage: Optional active storage selector.
    :return: Bootstrap summary used by diagnostics and tests.
    """
    return APP_CONFIG.bootstrap(
        env_files=env_files,
        env_file_overrides_os_environ=env_file_overrides_os_environ,
        load_dotenv_layers=load_dotenv_layers,
        storage=storage,
        logger=LOG,
    )


__all__ = [
    "APP_CONFIG",
    "APP_CONFIG_SPEC",
    "EnvBootstrapResult",
    "bootstrap_app_env",
]
