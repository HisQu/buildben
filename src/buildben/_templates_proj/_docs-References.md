# References

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Project and commands](#project-and-commands)
  - [Project paths](#project-paths)
  - [Command reference](#command-reference)
  - [Installer reference](#installer-reference)
  - [Uninstaller reference](#uninstaller-reference)
- [Configuration and Python interfaces](#configuration-and-python-interfaces)
  - [Environment variables](#environment-variables)
  - [Configuration files](#configuration-files)
  - [Public interfaces](#public-interfaces)
- [Development reference](#development-reference)
  - [Dependency declarations](#dependency-declarations)
  - [Figure visual tokens](#figure-visual-tokens)

<br>

# Project and commands

## Project paths

| Path | Responsibility |
| --- | --- |
| [README.md](../README.md) | Installation and first use. |
| [CHANGELOG.md](../CHANGELOG.md) | Release history and migration notes. |
| [BACKLOG.md](../BACKLOG.md) | Actionable work deferred from a change. |
| [AGENTS.md](../AGENTS.md) | Local coding and documentation rules. |
| [pyproject.toml](../pyproject.toml) | Package metadata, dependencies, and tool settings. |
| [justfile](../justfile) | Commands for [development and releases](Development.md#releases). |
| [cli/app.py](../src/{my_project}/cli/app.py) | The [command-line application](Explanations.md#command-line-application). |
| [config/app.py](../src/{my_project}/config/app.py) | The shared [AppRC](Explanations.md#apprc) declaration. |
| [config/sections/app.py](../src/{my_project}/config/sections/app.py) | The `AppSettings` [config section](Explanations.md#config-sections). |
| [config/bundle.py](../src/{my_project}/config/bundle.py) | The application's [config bundle](Explanations.md#config-bundle). |
| [<my_project> installation providers](../src/{my_project}/installation.py) | Typed hooks captured by the installed application runtime. |
| [tests](../tests) | Automated checks. |
| [examples](../examples) | Small user-facing programs, described in [Examples](EXAMPLES.md). |
| [docs](.) | Documentation, following the [authoring rules](README.md#documentation-rules). |

## Command reference

Run these commands from the [installed application environment](How-To-User-Guides.md#install-from-a-checkout).
Application resources use declared paths captured for the invocation; see
[configuration files](#configuration-files).

| Command | Result |
| --- | --- |
| `{my_project} --help` | Show application commands and AppRC's maintenance group without business setup. |
| `{my_project} launch` | Open the SDK-mounted Textual launcher. |
| `{my_project} version` | Print the installed package version. |
| `{my_project} app paths --json` | Inspect recorded application paths. |
| `{my_project} app doctor --json` | Diagnose installation state without resolving business settings. |
| `{my_project} app install -e` | Register the existing checkout environment as editable. |
| `{my_project} app repair` | Repair an eligible managed installation. |
| `{my_project} app uninstall --dry-run` | Preview program removal without mutation. |
| `{my_project} config show --json` | Print settings from the captured runtime snapshot. |
| `{my_project} config edit` | Open the optional config editor. |

Missing business settings do not disable the SDK-mounted launcher or
installation maintenance commands.

## Installer reference

`src/{my_project}_distr/make_artifacts.py` composes the authored application
declaration with `build_project_snapshot()` and `build_native_distribution()`.
Run `just make-artifacts [--revision REVISION]` to snapshot a committed Git
revision (default `HEAD`) and compile the Linux and Windows setup files.
Intermediates stay under `.cache/apprc`; final outputs are `dist/<app-id>-setup-linux-x86_64`,
`dist/<app-id>-setup-windows-x86_64.exe`, and `dist/SHA256SUMS`.
`just check-artifacts` is read-only: it validates declarations, the exact
checksum inventory, and the final setup bytes.

| Path | Purpose |
| --- | --- |
| `src/{my_project}/installation.py` | Installed application's shared typed `InstallationHooks`. |
| `src/{my_project}_distr/actions.py` | Authored native build actions; not imported as installed hooks. |
| `src/{my_project}_distr/make_artifacts.py` | Committed source preparation and ordinary/native package composition. |
| `src/{my_project}_distr/prepare.py` | Private-copy React build preparation, when enabled. |
| `src/{my_project}/_web/` | Built static frontend package data, when enabled. |

For React projects, `just build-python-packages` prepares the committed source
privately and builds only the declared workspace package's wheel/sdist under
`.cache/apprc/python-packages/`, without native compilation. Python-only projects
use plain `uv build` without an SDK authoring group or lockfile. Native setups
remain in `dist/`.

## Uninstaller reference

Use `{my_project} app uninstall --dry-run` to inspect removal. The default
program removal retains declared application resources; explicitly select
resource categories for deletion. Editable checkout files and environments are
never removal targets.

## Installation placement

The setup executable manages a native application runtime from the committed
snapshot. `app install -e` registers the existing `.venv` from the intended
checkout without managing its dependencies or files. Application resources are
placed using the declared native or single-root layout; the recorded absolute
paths are reused on reinstall. The resource layout does not relocate the
program environment, and changing layout does not move existing data.


Buildben does not adopt legacy installer receipts. The installer uses current
AppRC installation authority and lifecycle behavior; an old receipt is not a
source of installation identity, ownership, or recovery state. Install or
repair from an explicitly selected source rather than attempting receipt
adoption.

The current `installation migrate` management command is for explicit resource
and layout migration. A recorded migration resumes from its current lifecycle
authority after interruption. The fixed native `installation/` directory
remains separate from appdata and other declared resource capabilities.

Config, appdata, cache, and state are independent declared capabilities.
Disabled paths remain absent; an installation record does not enable appdata.

<br>

# Configuration and Python interfaces

## Environment variables

| Name | Meaning |
| --- | --- |
| `{MY_PROJECT}_MESSAGE` | Invocation override for `AppSettings.message`; see the [precedence example](EXAMPLES.md#an-invocation-override). |

The application loads environment files only when its declaration enables them.
Installer resource layout is selected with `--layout` and, for `single-root`,
`--root`; these are command-line options, not environment variables.

## Configuration files

| File | Meaning |
| --- | --- |
| [config/apprc.defaults.env](../src/{my_project}/config/apprc.defaults.env) | Defaults included in the installed package. |
| `<config path>/apprc.user.env` | Saved preferences only when user dotenv support is enabled. |

Resource locations are capabilities declared in `{my_project}.config.app.APP_RC`.
The saved installation authority records absolute paths for enabled resources;
it does not turn disabled resources on.

## Public interfaces

| Name | Responsibility |
| --- | --- |
| `{my_project}.config.app.APP_RC` | The shared `rc.AppRC` declaration. |
| `{my_project}.config.sections.app.AppSettings` | Typed application message and other business settings. |
| `{my_project}.config.bundle.{MyProject}Config` | Dataclass grouping application configuration sections. |
| `{my_project}.cli.app.app` | Typer command tree. |
| `{my_project}.main.main` | Entry point for the console script. |

Import config classes from these modules. The
[application-code guide](How-To-User-Guides.md#use-settings-in-application-code)
shows how `APP_RC.resolve()` and `ResolvedConfig.build()` construct them. The
[two-section example](EXAMPLES.md#several-config-sections) extends the bundle.

<br>

# Development reference

## Dependency declarations

| Declaration in `pyproject.toml` | Use |
| --- | --- |
| `[project].dependencies` | Published runtime requirements, including matching immutable Git sources for `apprc-core` and terminal `apprc`, plus `typer`. |
| `[project.optional-dependencies]` | Published extras for optional application features. |
| `[dependency-groups].dev` | Local authoring requirements, including `apprc-core[distribution]` from the matching SDK source commit. |

The scaffold pins AppRC core, terminal, and optional GUI sources to one immutable
Git commit. Ordinary pip reads the runtime source requirements directly;
runtime overrides preserve the same source identities in the uv-managed
application installation. These pins can include unreleased fixes. Buildben
itself keeps `dependencies=[]` and has no AppRC runtime reference or
application-data capabilities.

See the [package explanation](Explanations.md#package-layout-and-dependencies)
for wheel/sdist boundaries and [Development](Development.md#maintainer-environment)
for the locked authoring environment.

## Figure visual tokens

[Graphigs Theme](https://github.com/markur4/graphigs/blob/main/docs/Theme.md)
owns figure colors, strokes, fills, and typography. Follow the
[static figure rules](Development.md#static-figure-rules) when updating assets.
Keep captions and asset names here as the application gains figures; do not copy
the theme's rendered swatches into this repository.
