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
| [`{my_project}_distr`](../src/{my_project}_distr) | Authored lifecycle payload, generator, and SDK-produced management artifacts. |
| `app-install.sh` / `app-install.cmd` | Root install wrappers for POSIX and Windows. |
| `app-launch.sh` / `app-launch.cmd` | Root launch wrappers for POSIX and Windows. |
| `app-uninstall.sh` / `app-uninstall.cmd` | Root uninstall wrappers for POSIX and Windows. |
| [tests](../tests) | Automated checks. |
| [examples](../examples) | Small user-facing programs, described in [Examples](EXAMPLES.md). |
| [docs](.) | Documentation, following the [authoring rules](README.md#documentation-rules). |

## Command reference

Run these commands from the [installed application environment](How-To-User-Guides.md#install-from-a-checkout).
Application resources use declared paths captured for the invocation; see
[configuration files](#configuration-files).

| Command | Result |
| --- | --- |
| `{my_project} --help` | Show business commands and AppRC's Maintenance management panel without requiring business setup. |
| `{my_project} version` | Print the installed package version. |
| `{my_project} launcher` | Open the optional single-event-loop installed launcher. |
| `{my_project} installation show [--json]` | Inspect installation authority without mutation. |
| `{my_project} installation doctor [--json]` | Diagnose installation state without resolving business settings. |
| `{my_project} installation migrate --dry-run` | Preview an explicit resource or layout migration without writes. |
| `{my_project} installation repair [--installer PATH]` | Repair the saved installation using explicit matching support. |
| `{my_project} installation uninstall --dry-run` | Preview the selected uninstall without mutation. |
| `{my_project} config show --json` | Print the application config payload from its captured runtime snapshot. |
| `{my_project} config edit` | Open the optional config editor. |

`config show --json` contains package/version, paths, workspace selection, and
the current config payload. Missing business settings do not disable installation
show, doctor, dry-run, or repair management.

## Installer reference

`src/{my_project}_distr/make_artifacts.py` composes the authored lifecycle
payload with AppRC's deterministic generator. Run `just make-artifacts` after
editing it, and `just check-artifacts` to check tracked files without rewriting
them. The application wheel excludes `{my_project}_distr`; the source archive
includes the generator, payload, generated artifacts, and six root wrappers.

| Path | Purpose |
| --- | --- |
| `app-install.sh`, `app-install.cmd` | Install a checkout or selected release source. |
| `app-launch.sh`, `app-launch.cmd` | Launch the recorded installed command without environment recreation. |
| `app-uninstall.sh`, `app-uninstall.cmd` | Invoke the saved authored uninstallation procedure. |
| `src/{my_project}_distr/payload/app_lifecycle/install.py` | Repository-owned source acquisition and installation composition. |
| `src/{my_project}_distr/payload/app_lifecycle/uninstall.py` | Repository-owned uninstall preview and handoff composition. |
| `src/{my_project}_distr/artifacts/` | SDK-generated checkout payload; PowerShell remains under this tree. |

The default source is the current checkout when a local wrapper is used and the
published release source when a release wrapper is used. `--version X.Y.Z`
selects one published release. `--main` resolves remote `main` once to a full
commit identity. `--github-client gh` selects authenticated GitHub CLI transport;
it does not change source selection. For declared resource capabilities,
choose `--layout native` or `--layout single-root --root ABSOLUTE_PATH`. A
reinstall reuses saved absolute resource paths unless layout is explicitly
overridden.

An operating-system temporary directory may itself be a platform alias. The
installer resolves its private staging directory and read-only bootstrap package
transport paths before AppRC validation. Source identity and digest checks stay
unchanged; this does not allow symlinks in installation metadata or managed
application-resource paths.

Release preparation uses `just check-artifacts`, builds one validated wheel
and sdist, then runs `just stage-release-assets TAG FULL_COMMIT`. The helper
stages only the exact package pair and SDK-generated script entries in
`release/assets` and delegates manifest creation to the strict release asset
contract. Package builds do not generate artifacts or access the network.

## Uninstaller reference

`app-uninstall.sh` and `app-uninstall.cmd` route through the repository-authored
uninstall module and saved AppRC controller. The default retains declared
application resources and installation recovery support. Complete removal
requires selection of every tracked root, or explicit retention consent through
`--forget-retained`, followed by confirmation. A declared root is tracked even
when its directory is currently absent.

| Option | Effect |
| --- | --- |
| `--complete` | Remove lifecycle authority after every tracked root is selected or explicitly retained. |
| `--category config\|appdata\|cache\|state` | Select one owned resource category; repeat as needed. |
| `--forget-retained` | Consent to leaving unselected or unprovable files on disk while forgetting their installation authority. |
| `--yes` | Confirm the requested uninstall without an interactive prompt. |

The saved controller is kept under the fixed native
`installation/` directory, separate from appdata. Inspection and recovery use
`{my_project} installation show`, `{my_project} installation doctor`, and
`{my_project} installation repair`; these management commands do not require
business settings to resolve.

Project-specific cleanup belongs in ordinary repository functions called while
the program remains installed. Without `--forget-retained`, cleanup that cannot
prove ownership keeps the affected resource and installation authority for
recovery. With that explicit consent, retained files are not deleted. External
workspaces, shared uv, and shared Python are never inferred as removal targets.

## Installation placement

The installer supports `native` paths or one explicit `single-root` layout.
`--layout` and `--root` are installer options; `--root` is valid only with
`--layout single-root` and must be absolute. The saved placement records enabled
resource paths, which reinstallation reuses by default. This resource layout is
separate from the program environment: `uv tool install` manages the application
program in its tool environment, while `--layout` selects declared application
resource locations. Changing layout does not move the installed program or
automatically move existing resource contents.


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
| `[project].dependencies` | Published runtime dependencies, including `apprc>=0.31.0,<0.32` and `typer`. |
| `[project.optional-dependencies]` | Published extras for optional application features. |
| `[dependency-groups].dev` | Local authoring dependencies, including `apprc-core[distribution]>=0.31.0,<0.32`. |

The scaffold pins AppRC core, terminal, and optional GUI development sources to
one immutable integration commit until the matching AppRC release is published.
Runtime overrides pass the corresponding immutable source requirements to the
uv-managed application installation. Buildben itself keeps `dependencies=[]`
and has no AppRC runtime reference or application-data capabilities.

See the [package explanation](Explanations.md#package-layout-and-dependencies)
for wheel/sdist boundaries and [Development](Development.md#maintainer-environment)
for the locked authoring environment.

## Figure visual tokens

[Graphigs Theme](https://github.com/markur4/graphigs/blob/main/docs/Theme.md)
owns figure colors, strokes, fills, and typography. Follow the
[static figure rules](Development.md#static-figure-rules) when updating assets.
Keep captions and asset names here as the application gains figures; do not copy
the theme's rendered swatches into this repository.
