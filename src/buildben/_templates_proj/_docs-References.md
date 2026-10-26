# References

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Project and commands](#project-and-commands)
  - [Project paths](#project-paths)
  - [Command reference](#command-reference)
  - [Installer reference](#installer-reference)
  - [Uninstaller reference](#uninstaller-reference)
  - [Storage commands](#storage-commands)
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
| [distribution](../src/{my_project}_dev/distribution) | Canonical [installer scripts](#installer-reference). |
| [install-linux-macos.sh](../install-linux-macos.sh) | Root shortcut to the canonical Unix installer. |
| [install-windows.cmd](../install-windows.cmd) | Double-click entry point and root shortcut to the canonical Windows installer. |
| [uninstall.sh](../uninstall.sh) | Root shortcut to the saved Unix lifecycle helper. |
| [uninstall.cmd](../uninstall.cmd) | Native Windows shortcut to the saved lifecycle helper. |
| [tests](../tests) | Automated checks. |
| [examples](../examples) | Small user-facing programs, described in [Examples](EXAMPLES.md). |
| [docs](.) | Documentation, following the [authoring rules](README.md#documentation-rules). |

## Command reference

Run these commands in the [installed environment](How-To-User-Guides.md#install-from-a-cloned-repository).
Configuration commands use the AppRC directory selected by `{MY_PROJECT}_APPRC_DIR`.

| Command | Result |
| --- | --- |
| `{my_project} --help` | Show the command tree without requiring setup. |
| `python -m {my_project} --help` | Run the same application through Python. |
| `{my_project} version` | Print the installed package version. |
| `{my_project} diagnose --json` | Print package, interpreter, and AppRC paths. |
| `{my_project} config setup --yes --storage-root ROOT` | [Initialize storage](How-To-User-Guides.md#initialize-storage) and register it as `default`. |
| `{my_project} config doctor --json` | Inspect required values and source problems. |
| `{my_project} config paths --json` | Show configuration paths. |
| `{my_project} config show --json` | Build the [config bundle](Explanations.md#config-bundle) and print the application's configuration payload. |
| `{my_project} config set app.message TEXT --scope storage` | [Save a setting](How-To-User-Guides.md#edit-a-saved-setting) in the selected storage dotenv. |
| `{my_project} config edit` | Open the [config editor](Explanations.md#configuration-tools). |
| `{my_project} appdata paths --json` | Inventory managed files, internal roots, retained external roots, and stale registry state without creating files. |
| `{my_project} appdata clean --dry-run` | Preview managed-file and internal-root cleanup without deletion. |
| `{my_project} appdata clean --yes --apprc-dir PATH` | Clean the explicitly selected managed directory without resolving ordinary runtime settings; retain external payloads. |

`config show --json` contains `package`, `version`, `storage_name`, `storage_root`,
`storage_count`, and `config`. `config` holds the `AppSettings` fields. This shape
is defined by `_config_show_payload` in the application's CLI module.

## Installer reference

The canonical scripts live in `src/{my_project}_dev/distribution`. The root
[`install-linux-macos.sh`](../install-linux-macos.sh) and
[`install-windows.cmd`](../install-windows.cmd) files only forward arguments to
those scripts. The Windows CMD entry point runs a PowerShell policy preflight
before starting its installer.

| Script | Platform and role |
| --- | --- |
| `install-linux-macos.sh` | Bash installer for Linux and macOS. |
| `install-windows.cmd` | Windows entry point, including double-click support. |
| `install-windows.ps1` | Windows installer implementation. |
| `prepare-powershell-windows.cmd` | Handles RemoteSigned policy and downloaded-file marks for the Windows entry point. |
| `install-macos.command` | macOS double-click wrapper that forwards to the Bash installer. |

The scripts bootstrap from the repository's default branch in both modes.
Without a source option, they install the latest published stable source
distribution; `--version VERSION` selects a specific stable release. Release
installation uses the published release artifact. `--main` instead resolves
the current remote `main` branch once and downloads that commit's source
snapshot, including its committed `uv.lock`. It does not use local checkout
changes and requires no GitHub release or Actions artifact.

`--main` requires GitHub access: public requests use anonymous transport, while
`--github-client gh` uses authenticated GitHub CLI requests without anonymous
fallback. Install [GitHub CLI](https://cli.github.com/), then run `gh auth login` and `gh auth setup-git` when authenticated GitHub or private VCS access is needed. Public release downloads and curl do not inherit gh credentials.
private VCS dependencies separately need working Git credentials.

Main is unreleased code, and its CI may not have passed. The installed package
version comes from `pyproject.toml` and may match a release; the printed source
commit SHA identifies the selected snapshot. Omit `--main` or pass
`--version VERSION` to return to a release; `--main` and `--version` are
mutually exclusive.

| Option | Effect |
| --- | --- |
| *(no source option)* | Install the latest published stable release source archive. |
| `--version VERSION` | Select a stable release version, accepting `X.Y.Z` or `vX.Y.Z`; cannot be combined with `--main`. |
| `--main` | Install the current remote `main` snapshot pinned to one resolved commit and its committed lock file; requires GitHub access. |
| `--github-client curl` | Use anonymous public download transport (the default); Windows uses native PowerShell HTTP. |
| `--github-client gh` | Use authenticated GitHub CLI requests without anonymous fallback. |
| `--uv PATH` | Use a specific uv executable. |
| `--yes` | Skip the installer confirmation. |
| `--skip-config` | Skip `{my_project} config setup` after installation. |
| `--help` | Print the supported options. |

The release contains one standard wheel and one source archive. The installer
selects the matching source archive, requires its `pyproject.toml` and `uv.lock`,
exports the locked runtime requirements, and installs it with `uv tool
install`. A legacy source archive without `uv.lock` fails explicitly rather
than falling back to Git or another version. The normal release workflow reuses
one successful full CI gate for the exact tagged commit; it does not build
platform-specific installer archives.

## Uninstaller reference

Root `uninstall.sh` / `uninstall.cmd` dispatch to saved native launchers.
The canonical `src/{my_project}_dev/distribution/lifecycle.py` owns all deletion
policy and uses only the standard library. Native wrappers locate and launch
it; they do not duplicate removal logic. Saved launchers invoke absolute base
Python/helper paths without the source checkout, app environment, or PATH.

| Option | Effect |
| --- | --- |
| `--dry-run` | Preview only; never write state, download tools, clean data, or uninstall. |
| `--yes` | Confirm package removal only; required without a terminal for mutation. |
| `--clean-appdata` | Explicitly request application-managed cleanup before package removal, after machine-readable safety inventory and human preview. |
| `--apprc-dir PATH` | Forward an explicit directory only to `appdata` operations. |
| `--remove-uv` | Request separately authorized uv deletion only if every ownership, binary identity, and inventory check passes. |
| `--uv PATH` | Explicit package-only legacy recovery when a valid receipt is unavailable; cannot override a valid receipt's installation. |

Unix state is
`${XDG_STATE_HOME:-$HOME/.local/state}/<distribution_name>/installation`;
relative `XDG_STATE_HOME` is rejected. Windows state is
`%LOCALAPPDATA%\<distribution_name>\installation`, and missing `LOCALAPPDATA`
is an error. The private `receipt.json` stores distribution/command, installed
version/source ref, absolute base Python/uv/tool directories, appdata support,
bootstrap provenance and candidate hashes, and `package_removed` completion.
Saved helper/native launchers, Windows policy-preflight support, and receipt
remain after removal. Successful reinstall refreshes that same layout; a
conflicting layout, occupied unknown state directory, or linked state target
is rejected before package installation.

uv inventory uses the recorded directories, not later shell overrides.
Eligibility requires an owned standalone bootstrap, unchanged recorded regular
binaries, this package as the only tool before removal, and empty recorded and
default inventories afterward. Inventory parse/errors fail closed. Empty tool
inventories do not prove uv is unused by projects or prevent concurrent use.
Only enumerated binaries are unlinked, uv last; there is no recursive removal.

Cleanup runs the installed application at the recorded tool-bin path. Its
`appdata paths --json` inventory and `appdata clean --dry-run` must succeed
before deletion. Managed targets overlapping saved recovery support are
rejected. Failure/cancellation leaves the package installed. External payloads,
unmanaged data, shared Python, caches, and shell configuration are retained.
The [removal guide](How-To-User-Guides.md#remove-an-installation) covers practical
cleanup, recovery, and editable pip removal.

`appdata paths --json` returns `apprc_dir`, `managed_files`,
`internal_storage_roots`, `external_storage_roots`, `stale_storage`, and
`stale_user_dotenv`. `--apprc-dir` selects this managed inventory explicitly;
root runtime dotenv/storage selectors are not inherited. `appdata clean`
supports `--dry-run` and `--yes` / `-y`, with a separate default-No confirmation
when neither flag bypasses mutation.


## Storage commands

These commands act on the [storage registry](Explanations.md#storage). Names refer
to registered directories. `--storage NAME` before `config` selects one directory
for an invocation; [switching storage](How-To-User-Guides.md#switch-storage) shows
how that differs from changing the saved default.

| Command | Effect |
| --- | --- |
| `{my_project} config storage list` | List registered names and paths. |
| `{my_project} config storage add NAME ROOT --yes` | Register a directory and initialize its storage dotenv. |
| `{my_project} config storage select NAME` | Save a default for later invocations. |
| `{my_project} config storage move NAME ROOT` | Move the directory and update its registration. |
| `{my_project} config storage repoint NAME ROOT` | Reconnect a registration to a directory already at that path. |
| `{my_project} config storage remove NAME` | Unregister the directory, leaving its data on disk. |

<br>

# Configuration and Python interfaces

## Environment variables

| Name | Meaning |
| --- | --- |
| `{MY_PROJECT}_APPRC_DIR` | AppRC directory containing `apprc.toml`; defaults to `~/.local/share/{my_project}`. |
| `{MY_PROJECT}_STORAGE` | [Storage selector](Explanations.md#storage), accepting a registered name or a root path. |
| `{MY_PROJECT}_MESSAGE` | Invocation override for `AppSettings.message`; see the [precedence example](EXAMPLES.md#an-invocation-override). |

Shell values have higher precedence than saved dotenv values. The
[configuration-files explanation](Explanations.md#configuration-files) gives the
complete order. Setting `secret=True` redacts field display but does not encrypt
dotenv files.

## Configuration files

| File | Meaning |
| --- | --- |
| [config/apprc.defaults.env](../src/{my_project}/config/apprc.defaults.env) | Defaults included in the installed package. |
| `<AppRC directory>/apprc.toml` | Registry of storage names, paths, and the saved default. |
| `<storage root>/apprc.storage.env` | Overrides specific to one storage directory. |
| `<AppRC directory>/apprc.user.env` | Shared preferences, only if [user dotenv support is enabled](EXAMPLES.md#user-preferences-and-storage). |

The generated application enables storage but no user dotenv. Its
[setup guide](How-To-User-Guides.md#initialize-storage) creates the managed files
outside the installed package.

## Public interfaces

| Name | Responsibility |
| --- | --- |
| `{my_project}.config.app.APP_RC` | The shared `rc.AppRC` declaration. |
| `{my_project}.config.sections.app.AppSettings` | Typed `storage_root` and `message` settings. |
| `{my_project}.config.bundle.{MyProject}Config` | Dataclass grouping the application's config sections. |
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
| `[project].dependencies` | Runtime dependencies, initially `apprc>=0.29.0,<0.30` and `typer`. |
| `[project.optional-dependencies]` | Published extras for optional application features. |
| `[dependency-groups]` | Local maintainer tools such as pytest, Ruff, and Pyright. |

`apprc` installs the matching `apprc-core` and terminal libraries. Buildben itself
has no runtime dependency on AppRC. The generated application's
[package explanation](Explanations.md#package-layout-and-dependencies) describes
why each dependency is needed. [Contributing](../CONTRIBUTING.md#set-up-development)
provides the normal pip setup; [Development](Development.md#maintainer-environment)
covers uv and optional extras.

## Figure visual tokens

[Graphigs Theme](https://github.com/markur4/graphigs/blob/main/docs/Theme.md)
owns figure colors, strokes, fills, and typography. Follow the
[static figure rules](Development.md#static-figure-rules) when updating assets.
Keep captions and asset names here as the application gains figures; do not copy
the theme's rendered swatches into this repository.
