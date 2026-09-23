# References

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Project paths](#project-paths)
- [Command reference](#command-reference)
- [Storage commands](#storage-commands)
- [Environment variables](#environment-variables)
- [Configuration files](#configuration-files)
- [Public interfaces](#public-interfaces)
- [Dependency declarations](#dependency-declarations)
- [Figure visual tokens](#figure-visual-tokens)

## Project paths

| Path | Responsibility |
| --- | --- |
| [README.md](../README.md) | Installation and first use. |
| [CHANGELOG.md](../CHANGELOG.md) | Release history and migration notes. |
| [TODO.md](../TODO.md) | Actionable work deferred from a change. |
| [AGENTS.md](../AGENTS.md) | Local coding and documentation rules. |
| [pyproject.toml](../pyproject.toml) | Package metadata, dependencies, and tool settings. |
| [justfile](../justfile) | Commands for [development and releases](Development.md#releases). |
| [cli/app.py](../src/{my_project}/cli/app.py) | The [command-line application](Explanations.md#command-line-application). |
| [config/app.py](../src/{my_project}/config/app.py) | The shared [AppRC](Explanations.md#apprc) declaration. |
| [config/sections/app.py](../src/{my_project}/config/sections/app.py) | The `AppSettings` [config section](Explanations.md#config-sections). |
| [config/bundle.py](../src/{my_project}/config/bundle.py) | The application's [config bundle](Explanations.md#config-bundle). |
| [tests](../tests) | Automated checks. |
| [examples](../examples) | Small user-facing programs, described in [Examples](EXAMPLES.md). |
| [docs](.) | Documentation, following the [authoring rules](README.md#documentation-rules). |

## Command reference

Run these commands in the [installed environment](How-To-User-Guides.md#install-the-package).
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

`config show --json` contains `package`, `version`, `storage_name`, `storage_root`,
`storage_count`, and `config`. `config` holds the `AppSettings` fields. This shape
is defined by `_config_show_payload` in the application's CLI module.

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

## Dependency declarations

| Declaration in `pyproject.toml` | Use |
| --- | --- |
| `[project].dependencies` | Runtime dependencies, initially `apprc>=0.25.0,<0.26` and `typer`. |
| `[project.optional-dependencies]` | Published extras for optional application features. |
| `[dependency-groups]` | Local maintainer tools such as pytest, Ruff, and Pyright. |

`apprc` installs the matching `apprc-core` and terminal libraries. Buildben itself
has no runtime dependency on AppRC. The generated application's
[package explanation](Explanations.md#package-layout-and-dependencies) describes
why each dependency is needed. [Development](Development.md#maintainer-environment)
provides both pip and uv commands.

## Figure visual tokens

[Graphigs Theme](https://github.com/markur4/graphigs/blob/main/docs/Theme.md)
owns figure colors, strokes, fills, and typography. Follow the
[static figure rules](Development.md#static-figure-rules) when updating assets.
Keep captions and asset names here as the application gains figures; do not copy
the theme's rendered swatches into this repository.
