"""<my_project> runtime configuration declarations.

This module is the application-owned inventory that AppRC reuses for runtime
loading, validation, documentation, the generated config CLI, and the Textual
editor. Add new settings here before reading them from your runtime code.
"""

from __future__ import annotations

# == Standard Library ========================
from pathlib import Path

# == 3rd Party ===============================
from apprc.runtime_config.config_objects.env_config import EnvConfig
from apprc.runtime_config.config_objects.env_field import (
    config_owner_for,
    env_field,
    env_owner,
)
from apprc.runtime_config.contract.sentinels import (
    CONFIG_MISSING,
)


@env_owner(
    key="app",
    title="App",
    env_prefix="<MY_PROJECT>_",
    rc_path=("app",),
)
class AppRuntimeConfig(EnvConfig):
    """Typed application settings loaded from AppRC-managed env layers."""

    storage_root: Path = env_field(
        "STORAGE",
        default=CONFIG_MISSING,
        title="Storage root",
        explanation_short="Active local data root selected by AppRC.",
        explanation_long=(
            "The storage root is selected through the user-level AppRC "
            "registry, not by editing the storage-local dotenv file."
        ),
        editable=False,
        required=True,
    )
    message: str = env_field(
        "MESSAGE",
        default="Hello from <my_project>",
        title="Example message",
        explanation_short="Small editable example setting.",
        explanation_long=(
            "This field exists so a new scaffold immediately demonstrates "
            "`<my_project> config set app.message VALUE` and the Textual "
            "config editor. Replace it with real application settings."
        ),
    )


APP_CONFIG_ENVS = (AppRuntimeConfig,)
APP_CONFIG_OWNER = config_owner_for(AppRuntimeConfig)
ALL_CONFIG_OWNERS = (APP_CONFIG_OWNER,)
