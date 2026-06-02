"""Packaged configuration resources and AppRC adapter for <my_project>."""

# ruff: noqa: F401

from <my_project>.config.app import (
    APP_CONFIG,
    APP_CONFIG_SPEC,
    APP_ENV_BOOTSTRAP_SPEC,
    EnvBootstrapResult,
    bootstrap_app_env,
    make_config_editor_app,
)
from <my_project>.config.owners import (
    ALL_CONFIG_OWNERS,
    APP_CONFIG_OWNER,
)
