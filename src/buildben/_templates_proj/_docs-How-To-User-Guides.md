# How-to user guides

[Documentation](README.md) · [Explanations](Explanations.md) · [References](References.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Install the package](#install-the-package)
- [Run the first command](#run-the-first-command)
- [Initialize storage](#initialize-storage)
- [Edit a saved setting](#edit-a-saved-setting)
- [Switch storage](#switch-storage)
- [Add a setting](#add-a-setting)
- [Use settings in application code](#use-settings-in-application-code)
- [Troubleshoot configuration](#troubleshoot-configuration)

Each guide states its starting point. Commands use the generated application
name. Replace demonstration paths with your chosen directories for actual use.

## Install the package

From the generated project root, use Python 3.12 or newer:

```shell
python -m venv .venv
.venv/bin/python -m pip install -e .
```

On Windows use `.venv\Scripts\python.exe`. Activate the environment to run the
console commands below, or call `.venv/bin/{my_project}` directly. No `uv` command
is required. Installation requires AppRC 0.25.x; when testing before its release,
install the locally built `apprc_core` and `apprc` wheels in this environment first.
The [dependency reference](References.md#dependency-declarations) explains the
runtime and maintainer requirements.

## Run the first command

After [installation](#install-the-package), run:

```shell
{my_project} --help
python -m {my_project} --help
{my_project} version
{my_project} diagnose --json
```

Both help commands show the same Typer command tree. `version` prints the package
version; `diagnose` reports package, interpreter, and AppRC paths. These commands
work before [storage](Explanations.md#storage) is configured and create no files.

## Initialize storage

After installation, choose where configuration and data should live. This POSIX
example keeps data next to the checkout rather than inside it:

```shell
export {MY_PROJECT}_APPRC_DIR="$PWD/.demo-config"
{my_project} config setup --yes --storage-root ../{my_project}-data
{my_project} config doctor
{my_project} config show --json
```

On PowerShell set `$env:{MY_PROJECT}_APPRC_DIR = "$PWD/.demo-config"` instead.
Setup creates `.demo-config/apprc.toml`, registers the initial `default` storage,
and initializes its `apprc.storage.env`. Repeating setup for the same existing
root preserves data. Doctor reports ready settings, and show includes the
selected root and the starter `message`. The
[storage-only example](EXAMPLES.md#storage-only-application) explains the resulting files.

## Edit a saved setting

Start from an [initialized storage](#initialize-storage) and retain the same
`{MY_PROJECT}_APPRC_DIR` value in your shell:

```shell
{my_project} config set app.message "Hello local storage" --scope storage
{my_project} config show --json
{my_project} config edit
```

With `{MY_PROJECT}_MESSAGE` unset, show reports `Hello local storage`. The value
is saved in the selected directory's `apprc.storage.env`. The
[config editor](Explanations.md#configuration-tools) displays source values and
field help. A process value can override a successful edit, as the
[invocation example](EXAMPLES.md#an-invocation-override) demonstrates.

## Switch storage

Start from an initialized storage. Register another directory and try it for
one invocation:

```shell
{my_project} config storage add work ../{my_project}-work --yes
{my_project} --storage work config set app.message "Work data" --scope storage
{my_project} --storage work config show --json
{my_project} config storage select work
{my_project} config storage list
```

The explicit `--storage work` affects those invocations. `select work` then records
the saved default for later invocations. The [storage registry](Explanations.md#storage)
holds both registrations. [References](References.md#storage-commands) distinguishes
moving data, reconnecting a path, and unregistering a name.

## Add a setting

In [`AppSettings`](../src/{my_project}/config/sections/app.py), add this field
inside the existing class. This is a class-body excerpt:

```python
retries: int = rc.field(
    "{MY_PROJECT}_RETRIES",
    default=3,
    title="Request retries",
    explanation_short="Number of retries after a failed request.",
)
```

No separate CLI field list is needed. After setup, run
`{my_project} config set app.retries 5 --scope storage`, then
`{my_project} config show --json`. The `config` object contains integer `retries=5`.
The [config-field explanation](Explanations.md#config-sections) describes how the
Python type, key, default, and help text are used. For a second section, use the
[complete two-section example](EXAMPLES.md#several-config-sections).

## Use settings in application code

After installation and setup, save this complete program as `read_settings.py`
in the project root. Keep the same AppRC directory environment variable:

<!-- example-file: read_settings.py -->
```python
from {my_project}.config.app import APP_RC
from {my_project}.config.bundle import {MyProject}Config

resolved = APP_RC.resolve()
config = resolved.build({MyProject}Config)
print(config.app.message)
print(config.app.storage_root)
```

Run `python read_settings.py`. Pass `config` or `config.app` to application
functions that need these values. Within a Typer runtime command, obtain the
existing [`ResolvedConfig`](Explanations.md#resolvedconfig) from
`rc.cli.state_from(ctx, rc.cli.DefaultConfigCliState).resolved` instead of reading
inputs again. The [bundle](Explanations.md#config-bundle) groups sections for
passing them through application code.

## Troubleshoot configuration

Run `{my_project} config paths --json` to see which directory and registry the
current invocation uses. Run `{my_project} config doctor --json` to inspect
readiness without writing files.

| Symptom | Action |
| --- | --- |
| Command is unavailable | Use the installed environment's executable or `python -m {my_project}`. |
| Storage is missing | [Initialize it](#initialize-storage), or correct `{MY_PROJECT}_APPRC_DIR`. |
| A saved value does not win | Compare [configuration layers](Explanations.md#configuration-files), especially `{MY_PROJECT}_MESSAGE`. |
| A directory moved elsewhere | Use `config storage repoint NAME ROOT` to reconnect its existing path. |
| An edit reports a stale file | Inspect current values and make a fresh edit; do not reuse the old plan. |

The [command reference](References.md#command-reference) lists the commands and
links to their intended tasks.
