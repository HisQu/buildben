# How-to user guides

[Documentation](README.md) · [Explanations](Explanations.md) · [References](References.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Install and start](#install-and-start)
  - [Install a release](#install-a-release)
  - [Install from a checkout](#install-from-a-checkout)
  - [Run the first command](#run-the-first-command)
  - [Remove an installation](#remove-an-installation)
- [Configure settings and paths](#configure-settings-and-paths)
  - [Initialize saved preferences](#initialize-saved-preferences)
  - [Choose application paths](#choose-application-paths)
- [Extend and maintain configuration](#extend-and-maintain-configuration)
  - [Add a setting](#add-a-setting)
  - [Use settings in application code](#use-settings-in-application-code)
  - [Troubleshoot configuration and installation](#troubleshoot-configuration-and-installation)

Each guide states its starting point. Commands use the generated application
name. Replace demonstration paths with your chosen directories for actual use.

<br>

# Install and start

## Install a release

Download one release's exact assets, then run its native entry point:

```shell
gh release download vX.Y.Z --repo <github_username>/<my_project>
./app-install.sh
```

On Windows, run `.\app-install.cmd`. The release-mode native installer can
locate and verify its matching release assets without requiring an adjacent
`release-manifest.json` or `main-installer.py` beside the wrapper.

The default release selection installs the pinned source archive.
`--version X.Y.Z` selects one published version; `--main` resolves remote
`main` to a full immutable commit for that invocation. These options cannot be
combined. `--github-client gh` requests authenticated GitHub transport without
anonymous fallback. Private VCS dependencies separately need Git credentials.

## Install from a checkout

The checkout installer uses the actual local project files, including dirty
changes. First prepare the locked development environment and generated SDK
payload:

```shell
uv sync --locked --all-extras --all-groups
just make-artifacts
```

Then run `./app-install.sh --layout native` on Linux or macOS, or
`.\app-install.cmd --layout native` on Windows. Use
`--layout single-root --root ABSOLUTE_PATH` to select a single-root resource
layout. Reinstallation keeps its recorded absolute placement unless explicitly
overridden. `just check-artifacts` checks tracked generated files without
rewriting them.

## Run the first command

The generated command tree and installation management work before business
setup:

```shell
{my_project} --help
{my_project} version
{my_project} installation show
{my_project} installation doctor
{my_project} config show --json
```

The optional `{my_project} launcher` opens management and the installed command
in one Textual event loop. Missing business settings do not prevent installation
inspection or supported recovery.

## Remove an installation

Run `./app-uninstall.sh` on Linux or macOS, or `.\app-uninstall.cmd` on Windows.
The default removes the program and retains declared resources and saved
installation recovery support. Complete removal requires an explicit request:

```shell
./app-uninstall.sh --complete --category config --category appdata --yes
```

Repeat `--category` for each declared resource to remove. Unknown files and
external workspaces are not inferred as cleanup targets. If project cleanup
fails or cannot prove ownership, the saved record and affected resources remain
available for recovery. Use `{my_project} installation show`, `doctor`, or
`repair` when installation state is invalid or incomplete.

The saved helper is outside the removable program environment at the fixed
native `installation/` address. Changing `HOME`, XDG variables, or
`LOCALAPPDATA` later does not redirect a saved uninstall.

<br>

# Configure settings and paths

## Initialize saved preferences

The starter independently enables config and appdata and opts into a saved user
dotenv. Initialize user preferences, then inspect the app settings:

```shell
{my_project} config setup --yes
{my_project} config set app.message "Hello from my preferences" --scope user
{my_project} config show --json
```

The saved value is stored in `apprc.user.env` beneath the enabled config path.
An invocation environment variable such as `{MY_PROJECT}_MESSAGE` takes
precedence over a saved value. Use `{my_project} config edit` to inspect and
edit preferences interactively.


## Choose application paths

The installer selects `native` or one absolute `single-root` for declared
resources. A saved installation records the absolute config, appdata, cache,
and state paths that are enabled. Reinstalling preserves that placement unless
the installer receives an explicit layout override. The `installation/`
authority directory is separate from appdata and is never a resource-cleanup
target.

<br>

# Extend and maintain configuration

## Add a setting

In [`AppSettings`](../src/{my_project}/config/sections/app.py), add a field
inside the existing class. This is a class-body excerpt:

```python
retries: int = rc.field(
    "{MY_PROJECT}_RETRIES",
    default=3,
    title="Request retries",
    explanation_short="Number of retries after a failed request.",
)
```

No separate CLI field list is needed. After `{my_project} config setup --yes`,
save a user preference with
`{my_project} config set app.retries 5 --scope user`, then inspect it with
`{my_project} config show --json`. The [config-field explanation](Explanations.md#config-sections)
describes how the Python type, key, default, and help text are used. For a second
section, use the [complete two-section example](EXAMPLES.md#several-config-sections).

## Use settings in application code

Save this program as `read_settings.py` in the project root:

<!-- example-file: read_settings.py -->
```python

from {my_project}.config.app import APP_RC
from {my_project}.config.bundle import {MyProject}Config

resolved = APP_RC.resolve()
config = resolved.build({MyProject}Config)
print(config.app.message)
```

Run `python read_settings.py`. Pass `config` or `config.app` to application
functions that need these values. Within a Typer runtime command, obtain the
existing [`ResolvedConfig`](Explanations.md#resolvedconfig) from
`rc.cli.state_from(ctx, rc.cli.DefaultConfigCliState).resolved` instead of
reading inputs again. The [bundle](Explanations.md#config-bundle) groups
sections for passing through application code.

## Troubleshoot configuration and installation

Use `{my_project} config paths --json` to inspect captured application paths
and `{my_project} config doctor --json` to inspect settings without writing.
Use `{my_project} installation doctor` to diagnose saved installation
authority; it does not require successful business configuration.

| Symptom | Action |
| --- | --- |
| Command is unavailable | Use the installed environment's executable or `python -m {my_project}`. |
| A saved setting does not win | Compare [configuration layers](Explanations.md#configuration-files), especially `{MY_PROJECT}_MESSAGE`. |
| Saved installation paths differ from the current environment | Inspect `{my_project} installation show`; reinstallation retains recorded paths unless explicitly overridden. |
| Installation authority is invalid or incomplete | Use `installation doctor` and follow the matching `installation repair` guidance. |

The [command reference](References.md#command-reference) lists supported
commands and links to their intended tasks.
