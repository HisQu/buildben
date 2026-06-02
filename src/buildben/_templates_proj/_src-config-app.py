"""<my_project>-bound AppRC configuration adapter."""

from __future__ import annotations

# == Standard Library ========================
from pathlib import Path
from typing import Any

# == 3rd Party ===============================
from apprc import AppConfigKit
from apprc.config.environment import EnvBootstrapResult
from apprc.config.storage_registry import StorageRegistry
from apprc.logging import get_logger

# == Internal ================================
from <my_project>.config.owners import ALL_CONFIG_OWNERS

LOG = get_logger(__name__)

APP_CONFIG = AppConfigKit(
    app_name="<my_project>",
    display_name="<my_project>",
    config_package="<my_project>.config",
    owners=ALL_CONFIG_OWNERS,
    storage_root_env_key="<MY_PROJECT>_STORAGE",
    registry_filename="<my_project>.toml",
    shared_env_filename=".env.shared",
    local_env_filename=".env.local",
)
APP_CONFIG_SPEC = APP_CONFIG.spec
APP_ENV_BOOTSTRAP_SPEC = APP_CONFIG_SPEC.env_bootstrap_spec()


def bootstrap_app_env(
    *,
    env_file: Path | None,
    env_file_overrides_shell: bool,
    no_dotenv: bool,
    storage_name: str | None,
) -> EnvBootstrapResult:
    """Populate ``os.environ`` for one <my_project> CLI process.

    :param env_file: Optional explicit dotenv file.
    :param env_file_overrides_shell: Whether the explicit dotenv file beats
        exported shell variables inside this process.
    :param no_dotenv: Whether packaged and local dotenv files are skipped.
    :param storage_name: Optional named storage selector.
    :return: Bootstrap summary used by diagnostics and tests.
    """
    return APP_CONFIG.bootstrap(
        env_file=env_file,
        env_file_overrides_shell=env_file_overrides_shell,
        no_dotenv=no_dotenv,
        storage_name=storage_name,
        logger=LOG,
    )


def make_config_editor_app(
    *,
    registry: StorageRegistry,
    initial_storage: str | None = None,
) -> Any:
    """Build the Textual config editor lazily.

    :param registry: Storage registry shown by the editor.
    :param initial_storage: Optional storage selected on startup.
    :return: Textual application instance.
    """
    return APP_CONFIG.editor_app(
        registry=registry,
        initial_storage=initial_storage,
    )


__all__ = [
    "APP_CONFIG",
    "APP_CONFIG_SPEC",
    "APP_ENV_BOOTSTRAP_SPEC",
    "EnvBootstrapResult",
    "bootstrap_app_env",
    "make_config_editor_app",
]
