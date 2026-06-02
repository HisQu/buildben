"""<my_project> configuration owner specs.

This module is the application-owned inventory that AppRC reuses for runtime
loading, validation, documentation, the generated config CLI, and the Textual
editor. Add new settings here before reading them from your runtime code.
"""

from __future__ import annotations

# == Standard Library ========================
from pathlib import Path

# == 3rd Party ===============================
from apprc.config import CONFIG_MISSING, ConfigOwner, config_field

APP_CONFIG_OWNER = ConfigOwner(
    key="app",
    title="App",
    env_prefix="<MY_PROJECT>_",
    rc_path=("app",),
    runtime_cls=None,
    fields=(
        config_field(
            "storage_root",
            "STORAGE",
            Path,
            default=CONFIG_MISSING,
            title="Storage root",
            explanation_short="Active local data root selected by AppRC.",
            explanation_long=(
                "The storage root is selected through the user-level AppRC "
                "registry, not by editing the storage-local dotenv file."
            ),
            editable=False,
            required=True,
        ),
        config_field(
            "message",
            "MESSAGE",
            str,
            default="Hello from <my_project>",
            title="Example message",
            explanation_short="Small editable example setting.",
            explanation_long=(
                "This field exists so a new scaffold immediately demonstrates "
                "`<my_project> config set app.message VALUE` and the Textual "
                "config editor. Replace it with real application settings."
            ),
        ),
    ),
)

ALL_CONFIG_OWNERS = (APP_CONFIG_OWNER,)
