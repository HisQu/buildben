# How-to user guides

[Documentation](README.md) · [Explanations](Explanations.md) · [References](References.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Install and start](#install-and-start)
  - [One-line install](#one-line-install)
  - [Install from a cloned repository](#install-from-a-cloned-repository)
  - [Run the first command](#run-the-first-command)
  - [Remove an installation](#remove-an-installation)
- [Configure storage and settings](#configure-storage-and-settings)
  - [Initialize storage](#initialize-storage)
  - [Edit a saved setting](#edit-a-saved-setting)
  - [Switch storage](#switch-storage)
- [Extend and maintain configuration](#extend-and-maintain-configuration)
  - [Add a setting](#add-a-setting)
  - [Use settings in application code](#use-settings-in-application-code)
  - [Troubleshoot configuration](#troubleshoot-configuration)

Each guide states its starting point. Commands use the generated application
name. Replace demonstration paths with your chosen directories for actual use.

<br>

# Install and start

## One-line install

The one-line installer bootstraps from the repository's current `main` branch
in both modes. By default it installs the latest stable release source
distribution; `--version X.Y.Z` selects a specific stable release. A release
install uses the published release artifact. `--main` instead installs one
snapshot of the current remote `main`, pinned to the commit resolved for that
invocation and its committed `uv.lock`; local checkout changes are not used,
and no GitHub release or Actions artifact is required.

`--main` requires GitHub access. Public downloads use anonymous requests;
authenticated access uses GitHub CLI and requires `gh auth login` and
`gh auth setup-git`. Main may contain unreleased code whose CI has not passed.
The installed version comes from `pyproject.toml` and may match a release; the
installer prints the source commit SHA to identify the snapshot. Omit `--main`,
or use `--version`, to install a release again. These options cannot be combined.

Public installation is the default: curl on Linux and macOS, and native
PowerShell HTTP on Windows. Private VCS dependencies still need working Git
credentials independently.

### For Linux & macOS

Public:

```shell
installer="$(curl -fsSL https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-linux-macos.sh)" && test -n "$installer" && bash -c "$installer" -- --main
```

Authenticated:

```shell
installer="$(gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-linux-macos.sh')" && test -n "$installer" && bash -c "$installer" -- --github-client gh --main
```

### For Windows

Public:

```powershell
$url = 'https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-windows.ps1'; $installer = Invoke-RestMethod -Uri $url; if ([string]::IsNullOrWhiteSpace(($installer -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($installer -join "`n"))) '--main'
```

Authenticated:

```powershell
$s = gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-windows.ps1'; if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($s -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($s -join "`n"))) '--github-client' 'gh' '--main'
```
See the [installer reference](References.md#installer-reference) for all
supported options and release selection details.

### For Linux & macOS

Public:

```shell
installer="$(curl -fsSL https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-linux-macos.sh)" && test -n "$installer" && bash -c "$installer" --
```

Authenticated:

```shell
installer="$(gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-linux-macos.sh')" && test -n "$installer" && bash -c "$installer" -- --github-client gh
```

### For Windows

Public:

```powershell
$url = 'https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-windows.ps1'; $installer = Invoke-RestMethod -Uri $url; if ([string]::IsNullOrWhiteSpace(($installer -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($installer -join "`n")))
```

Authenticated:

```powershell
$s = gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-windows.ps1'; if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($s -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($s -join "`n"))) '--github-client' 'gh'
```

If uv is missing, the installer asks before installing the pinned version. See
the [installer reference](References.md#installer-reference) for supported
options and the distinction between public and authenticated transport.

After installation, the installer runs `{my_project} config setup`, which guides
you through initial configuration.

## Install from a cloned repository

From the project directory, install with Python 3.12 or newer. This workflow
uses a virtual environment and pip and does not require uv:

### For Linux & macOS

```shell
python -m venv .venv
.venv/bin/python -m pip install -e .
```

### For Windows

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -e .
```

Activate the environment to run the console commands below, or call
`.venv/bin/{my_project}` on Linux or macOS and
`& '.\.venv\Scripts\{my_project}.exe'` on Windows. Installation requires
`apprc>=0.25.0,<0.26`; the install command
resolves it and its dependencies from PyPI. The
[dependency reference](References.md#dependency-declarations) lists runtime
and maintainer requirements.

uv is optional for cloned-repository development. Use `uv sync` from the
repository root if you prefer uv; the installer itself has no developer or
editable-clone mode. The
[`just sync` recipe](Development.md#maintainer-environment) prepares the locked
development environment.

## Run the first command

After [installation](#install-from-a-cloned-repository) or a [one-line install](#one-line-install), run:

```shell
{my_project} --help
python -m {my_project} --help
{my_project} version
{my_project} diagnose --json
```

Both help commands show the same Typer command tree. `version` prints the package
version; `diagnose` reports package, interpreter, and AppRC paths. These commands
work before [storage](Explanations.md#storage) is configured and create no files.

## Remove an installation

For a one-line installation, remove the application with
`uv tool uninstall {my_project}`. For an editable install from a cloned
repository, run `.venv/bin/python -m pip uninstall {my_project}` on Linux or
macOS, or `& '.\.venv\Scripts\python.exe' -m pip uninstall {my_project}` in
Windows PowerShell. Remove the clone and its `.venv` when you no longer need
them.

If the one-line installer also installed uv in the default directory, remove
its executables:

Linux and macOS:

```shell
rm -f ~/.local/bin/uv ~/.local/bin/uvx ~/.local/bin/uvw
```

Windows PowerShell:

```powershell
Remove-Item -ErrorAction SilentlyContinue "$HOME\.local\bin\uv.exe", "$HOME\.local\bin\uvx.exe", "$HOME\.local\bin\uvw.exe"
```

See Astral's [uv uninstallation guide](https://docs.astral.sh/uv/getting-started/installation/#uninstallation)
for other install locations and optional data cleanup.

<br>

# Configure storage and settings

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

<br>

# Extend and maintain configuration

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
