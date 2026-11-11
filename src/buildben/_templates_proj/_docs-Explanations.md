# Explanations

[Documentation](README.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Application and settings](#application-and-settings)
  - [Command-line application](#command-line-application)
  - [AppRC](#apprc)
  - [Config sections](#config-sections)
  - [ResolvedConfig](#resolvedconfig)
- [Files and paths](#files-and-paths)
  - [Configuration files](#configuration-files)
  - [Filesystem capabilities](#filesystem-capabilities)
- [Tools and package structure](#tools-and-package-structure)
  - [Configuration tools](#configuration-tools)
  - [Config bundle](#config-bundle)
  - [Package layout and dependencies](#package-layout-and-dependencies)

This page describes the generated application's components. As the application
grows, explain each new component and connect it to these existing components.

<br>

# Application and settings

## Command-line application

The command-line application is the Typer `app` in
[`cli/app.py`](../src/{my_project}/cli/app.py). Both the console script and
`python -m {my_project}` run this object. AppRC mounts configuration and
installation-management commands in its Maintenance help panel. Installation
show, doctor, migration dry-run, repair, and uninstall preview are available
without resolving ordinary business settings.

The optional `launcher` uses one Textual event loop for management and the
installed application's command. It captures layout, workspace, dotenv, and
environment controls from the initiating CLI context. Application startup and
uninstall remain separate actions; the launcher does not recreate environments
or run business setup merely to show management.

## AppRC

`APP_RC` in [`config/app.py`](../src/{my_project}/config/app.py) is the shared
`rc.AppRC` declaration. It identifies the application, independently enables
config and appdata paths, and optionally declares saved user dotenv support.
Installation state is recorded separately from these application resources.
The declaration enables only the capabilities the application uses; an
installation receipt cannot enable an undeclared path.

## Config sections

A config section is a class of related business settings. The starter's
[`AppSettings`](../src/{my_project}/config/sections/app.py) contains `message`.
Each `rc.field(...)` connects a Python attribute to an environment key and
supplies its default and help text. Add fields here or add a focused section
when the application needs more business settings.

Field `title`, `explanation_short`, and `explanation_long` are reused by the
config editor. Use `secret=True` for redacted display of sensitive values; this
flag does not encrypt stored values.

## ResolvedConfig

A `ResolvedConfig` contains the values read for one invocation. The mounted CLI
calls `APP_RC.resolve()` and stores the result as `state.resolved`.
`resolved.build({MyProject}Config)` converts those inputs into the application's
[config bundle](#config-bundle).

For example, `{MY_PROJECT}_MESSAGE=hello` supplies a string to the `message`
field. Each result retains the values it read; a later environment change does
not mutate an earlier result or `os.environ`.
The [application-code guide](How-To-User-Guides.md#use-settings-in-application-code)
shows how to construct settings explicitly outside the CLI.

<br>

# Files and paths

## Configuration files

The starter reads configuration from Python defaults, packaged defaults, the
optional saved user dotenv, explicit dotenv files, and process environment.
Later values replace earlier values for the same key. The configuration
declaration controls which files are loaded; installation management does not
require them to be readable.

## Filesystem capabilities

AppRC declares config, appdata, cache, and state independently. Each enabled
resource has one captured absolute path in the installation placement; disabled
resources remain absent. A native layout uses platform locations. A
single-root layout uses `config/`, `appdata/`, `cache/`, and `state/` beneath
one absolute root. Reinstallation reuses recorded paths unless an explicit
layout override is supplied.

The fixed native `installation/` directory is separate from appdata and is
never a purgeable capability. It contains the authoritative installation
record and saved management support required for repair and recovery.

<br>

# Tools and package structure

## Configuration tools

`APP_RC.manage()` returns a `ConfigManager` that initializes declared files,
inspects settings, and plans edits. It provides the same operations to Python
code and the interactive interfaces. Creating a manager does not write.

The config CLI is the `config` command group mounted on Typer. `config doctor`
reports missing values and source problems; `config set` saves an override;
`config edit` opens the Textual config editor. The
[editing guide](How-To-User-Guides.md#initialize-saved-preferences) shows which file changes.

The config editor displays effective values and their contributing layers. It
can edit saved user or workspace overrides, but it does not rewrite packaged
defaults or the parent shell's environment. Opening it writes nothing; setup and
save are explicit actions.

## Config bundle

A config bundle is a dataclass containing config sections. The starter's
[`{MyProject}Config`](../src/{my_project}/config/bundle.py) contains one `app`
section. Adding another section gives application code another named attribute
without mixing unrelated settings into one class.

`@APP_RC.bundle` registers the dataclass. `resolved.build({MyProject}Config)`
constructs its registered section factories from the same `ResolvedConfig`.
The [two-section example](EXAMPLES.md#several-config-sections) shows the
additional class and bundle field. Importing the bundle imports its sections;
there is no separate config catalog.

## Package layout and dependencies

Runtime source lives under `src/{my_project}`. Package initializers stay small;
commands import the declaration and bundle directly from their modules. The
[project paths](References.md#project-paths) table identifies each source file,
and [Development](Development.md#repository-routing) explains where to add code.

`[project].dependencies` declares `apprc-core` and terminal `apprc` from the same
immutable Git commit, so ordinary pip installations use matching SDK sources.
The local `dev` dependency group adds `apprc-core[distribution]` from that commit
for artifact generation; the optional GUI group uses its matching `apprc-gui`
source. Runtime overrides preserve those source identities in uv-managed
installations. Source pins can include unreleased fixes and do not imply that
the published SDK version has the same code. Buildben itself keeps
`dependencies=[]` and does not depend on AppRC at runtime.
