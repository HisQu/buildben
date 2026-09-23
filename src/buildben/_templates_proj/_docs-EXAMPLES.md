# Examples

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Development](Development.md)

- [Storage-only application](#storage-only-application)
- [An invocation override](#an-invocation-override)
- [User preferences and storage](#user-preferences-and-storage)
- [Several config sections](#several-config-sections)

These examples start from the installed generated project. Each states the
files it changes and the result to expect. Use a disposable checkout when
trying examples that replace Python modules.

## Storage-only application

The starter already declares `rc.Storage()` on its shared
[`APP_RC`](Explanations.md#apprc). No source changes are needed. In the project
root, run this complete POSIX shell sequence:

```shell
export {MY_PROJECT}_APPRC_DIR="$PWD/.example-config"
unset {MY_PROJECT}_STORAGE {MY_PROJECT}_MESSAGE
{my_project} config setup --yes --storage-root ../{my_project}-example-data
{my_project} config set app.message "My saved message" --scope storage
{my_project} config show --json
```

The output's `config.message` is `My saved message`. The
[storage registry](Explanations.md#storage) is `.example-config/apprc.toml`;
`../{my_project}-example-data/apprc.storage.env` stores the message. Application
data can live in that same directory, outside the checkout. The
[application-code guide](How-To-User-Guides.md#use-settings-in-application-code)
shows how to obtain `config.app.storage_root` for writing data.

## An invocation override

Starting from an installed project, this sequence uses its own AppRC directory
and storage. POSIX shell syntax supplies one environment value to one command:

```shell
export {MY_PROJECT}_APPRC_DIR="$PWD/.override-config"
unset {MY_PROJECT}_STORAGE {MY_PROJECT}_MESSAGE
{my_project} config setup --yes --storage-root ../{my_project}-override-data
{my_project} config set app.message "Saved value" --scope storage
{MY_PROJECT}_MESSAGE="One invocation" {my_project} config show --json
{my_project} config show --json
```

The first show prints `One invocation`; the second prints `Saved value`.
The environment value changes no file. The [configuration layers](Explanations.md#configuration-files)
explain that precedence; the [editing guide](How-To-User-Guides.md#edit-a-saved-setting)
shows how to make a persistent edit.

## User preferences and storage

Start from an unchanged generated project. To allow preferences shared across
storages, replace `src/{my_project}/config/app.py` with this complete module:

<!-- example-file: src/{my_project}/config/app.py -->
```python
import apprc as rc

APP_RC = rc.AppRC(
    app_id="{my_project}",
    display_name="{MyProject}",
    config_package="{my_project}.config",
    user_dotenv=rc.UserDotenv(),
    storage=rc.Storage(selector_env_key="{MY_PROJECT}_STORAGE"),
    command_name="{my_project}",
)
```

After installing the changed project, run this independent POSIX sequence:

```shell
export {MY_PROJECT}_APPRC_DIR="$PWD/.preferences-config"
unset {MY_PROJECT}_STORAGE {MY_PROJECT}_MESSAGE
{my_project} config setup --yes --storage-root ../{my_project}-preferences-data
{my_project} config set app.message "Shared preference" --scope user
{my_project} config show --json
{my_project} config set app.message "This storage only" --scope storage
{my_project} config show --json
```

The first show prints `Shared preference`, saved in `apprc.user.env`. The second
prints `This storage only`, saved in `apprc.storage.env`. A storage value wins over
a user value. [References](References.md#configuration-files) locates both files.
The config editor now offers both editable layers.

## Several config sections

Start from an unchanged generated project. Add this complete file at
`src/{my_project}/config/sections/client.py`:

<!-- example-file: src/{my_project}/config/sections/client.py -->
```python
import apprc as rc

from {my_project}.config.app import APP_RC


@APP_RC.config("client", prefix="{MY_PROJECT}_", rc_path=("client",))
class ClientSettings(rc.Config):
    timeout: int = rc.field(
        "{MY_PROJECT}_TIMEOUT",
        default=30,
        explanation_short="Seconds to wait for a server response.",
    )
```

Replace `src/{my_project}/config/bundle.py` with:

<!-- example-file: src/{my_project}/config/bundle.py -->
```python
from dataclasses import dataclass, field

from {my_project}.config.app import APP_RC
from {my_project}.config.sections.app import AppSettings
from {my_project}.config.sections.client import ClientSettings


@APP_RC.bundle
@dataclass(kw_only=True)
class {MyProject}Config:
    app: AppSettings = field(default_factory=AppSettings)
    client: ClientSettings = field(default_factory=ClientSettings)
```

Save this complete program as `read_sections.py` in the project root:

<!-- example-file: read_sections.py -->
```python
from {my_project}.config.app import APP_RC
from {my_project}.config.bundle import {MyProject}Config

resolved = APP_RC.resolve()
config = resolved.build({MyProject}Config)
print(config.app.message)
print(config.client.timeout)
```

After installing the changed project, run:

```shell
export {MY_PROJECT}_APPRC_DIR="$PWD/.sections-config"
unset {MY_PROJECT}_STORAGE {MY_PROJECT}_MESSAGE {MY_PROJECT}_TIMEOUT
{my_project} config setup --yes --storage-root ../{my_project}-sections-data
python read_sections.py
{my_project} config set client.timeout 10 --scope storage
python read_sections.py
```

The timeout changes from `30` to `10`. The [config bundle](Explanations.md#config-bundle)
passes both sections together. The starter's `config show --json` callback still
prints only `config.app`; extend `_config_show_payload` in `cli/app.py` if the
application should include `client` in that JSON output too.
