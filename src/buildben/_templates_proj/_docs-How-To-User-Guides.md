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
- [Develop the optional React frontend](#develop-the-optional-react-frontend)

Each guide states its starting point. Commands use the generated application
name. Replace demonstration paths with your chosen directories for actual use.

<br>

# Install and start

## Install a release

Download the native setup for your platform and `SHA256SUMS`, then run the
setup:

```shell
gh release download vX.Y.Z --repo <github_username>/<my_project>
./<my_project>-setup-linux-x86_64
```

On Windows, run `<my_project>-setup-windows-x86_64.exe`. `SHA256SUMS` covers
exactly the two setup files. Cross-compilation does not establish Windows
runtime behavior.

## Install from a checkout

From the intended checkout, synchronize the existing locked environment and
register that checkout as an editable application:

```shell
uv sync --locked --all-extras --all-groups
uv run --locked <my_project> app install -e
```

Editable registration does not copy source, create an environment, or resolve
dependencies. Restore a broken development environment with `uv sync --locked`.
`just make-artifacts` builds native setup files from the committed Git snapshot;
`just check-artifacts` checks declarations and final checksums without writing.

## Run the first command

Application commands and maintenance remain available before business setup:

```shell
<my_project> --help
<my_project> version
<my_project> paths --json
<my_project> app doctor
<my_project> config show --json
```

`{my_project} launch` opens management and the installed command through
AppRC's SDK-mounted Textual launcher. Installation paths and hooks come from the
recorded application authority.

## Remove an installation

Run `<my_project> app uninstall --dry-run` to inspect removal, then
`<my_project> app uninstall --yes` to remove the program while retaining
declared resources. Select resource categories explicitly before deleting them.
Unknown files, checkouts, and developer environments are not cleanup targets.

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

Use `{my_project} app paths --json` to inspect captured application paths and
`{my_project} config doctor --json` to inspect settings without writing.
`{my_project} app doctor` diagnoses installation authority without requiring
successful business configuration.

| Symptom | Action |
| --- | --- |
| Command is unavailable | Use the installed environment's executable or `python -m {my_project}`. |
| A saved setting does not win | Compare [configuration layers](Explanations.md#configuration-files), especially `{MY_PROJECT}_MESSAGE`. |
| Saved installation paths differ from the current environment | Inspect `{my_project} app paths`; reinstalling reuses the recorded paths unless changed explicitly. |
| Installation authority is invalid or incomplete | Use `{my_project} app doctor` and follow the reported repair guidance. |

The [command reference](References.md#command-reference) lists supported
commands and links to their intended tasks.

<br>

# Develop the optional React frontend

This section applies only when the project was generated with Buildben's
`--frontend react` option. Python-only scaffolds have no frontend module.
Use Node 24.22.2+ within the Node 24 line, Bun >=1.4.4, and just with module
support; CI uses Bun 1.4.4 and just 1.56.0.

From the project root, run:

```shell
just --list front
just front sync
just front dev
```

The module runs from `frontend/`, so no directory wrapper is needed. Its
`package.json` owns React, Vite, TypeScript, ESLint, and Vitest; `bun.lock`
records their resolved dependencies. Sync uses `bun install --frozen-lockfile`
and must not rewrite either file. To add Vite manually to an existing
frontend, run `bun add -d vite` inside its directory, then commit the manifest
and lockfile; do not put this command in global provisioning.

Before committing frontend changes, run the frontend checks and Python package
test:

```shell
just front check
just front test
just front build
uv run --locked pytest tests/test_web.py
```

The Python test builds a wheel and sdist from a committed private source copy,
then serves the installed wheel's HTML through the standard-library server. It
requires Bun for React asset preparation but does not build native setups or
write `_web/`, `frontend/dist/`, or `node_modules/` into the checkout. Release
package builds use the same locked preparation and select only this workspace
package; run `just build-python-packages` to build them manually. Python-only
scaffolds need no Bun and keep their normal package build path. Do not put
secrets in browser-visible Vite environment variables.
