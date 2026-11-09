# Examples

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Development](Development.md)

- [Read saved settings in Python](#read-saved-settings-in-python)
- [An invocation override](#an-invocation-override)
- [Several config sections](#several-config-sections)

These examples start from the installed generated project. Each states the
files it changes and the result to expect. Use a disposable checkout when
trying examples that replace Python modules.

<br>

# Read saved settings in Python

Save this program as `read_settings.py` in the project root:

<!-- example-file: read_settings.py -->
```python
from {my_project}.config.app import APP_RC
from {my_project}.config.bundle import {MyProject}Config

resolved = APP_RC.resolve()
config = resolved.build({MyProject}Config)
print(config.app.message)
```

Run `{my_project} config setup --yes` and then
`{my_project} config set app.message "My saved message" --scope user` before
running `python read_settings.py`. It prints the effective setting. A process
environment override such as `{MY_PROJECT}_MESSAGE` takes precedence without
changing the saved dotenv. See
[configuration layers](Explanations.md#configuration-files) and the
[configuration editor guide](How-To-User-Guides.md#initialize-saved-preferences).

<br>

# An invocation override

With saved preferences from [Read saved settings in Python](#read-saved-settings-in-python),
run this command from the project root:

```shell
{MY_PROJECT}_MESSAGE="Only for this command" python read_settings.py
```

The process receives the environment override, so the program prints
`Only for this command` instead of the saved value. The saved user dotenv is
unchanged. See [configuration layer precedence](Explanations.md#configuration-files).

<br>

# Several config sections

Start from an unchanged generated project. Add this complete file at
`src/{my_project}/config/sections/client.py`:

<!-- example-file: src/{my_project}/config/sections/client.py -->
```python
import apprc as rc

from {my_project}.config.app import APP_RC


@APP_RC.config("client", prefix="{MY_PROJECT}_")
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

Run the new program with a process-local override:

```shell
{MY_PROJECT}_TIMEOUT=10 python read_sections.py
```

The output uses the new `client.timeout` value while preserving the default
when the variable is absent. The [config bundle](Explanations.md#config-bundle)
passes both sections together. Extend `_config_show_payload` in
`src/{my_project}/cli/app.py` if the application should include `client` in its
`config show --json` output too.
