# Explanations

[Documentation](README.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Examples](EXAMPLES.md) · [Development](Development.md)

- [Command-line application](#command-line-application)
- [AppRC](#apprc)
- [Config sections](#config-sections)
- [ResolvedConfig](#resolvedconfig)
- [Configuration files](#configuration-files)
- [Storage](#storage)
- [Configuration tools](#configuration-tools)
- [Config bundle](#config-bundle)
- [Package layout and dependencies](#package-layout-and-dependencies)

This page describes the generated application's components. As the application
grows, explain each new component and connect it to these existing components.

## Command-line application

The command-line application is the Typer `app` in
[`cli/app.py`](../src/{my_project}/cli/app.py). Both the `{my_project}` console
script and `python -m {my_project}` run that object. The starter provides
`version` and `diagnose`; AppRC adds the `config` commands.

`version` and `diagnose` can run before storage is configured. Runtime configuration
commands such as `config show` need selected storage. The
[first-command guide](How-To-User-Guides.md#run-the-first-command) demonstrates
that distinction. Add application commands to this command tree rather than
creating a second entrypoint with different configuration behavior.

## AppRC

`APP_RC` in [`config/app.py`](../src/{my_project}/config/app.py) is one `rc.AppRC`
declaration shared by the command-line application and its settings. It records
`app_id="{my_project}"`, the package containing defaults, and storage support.
The starter enables `rc.Storage()` but does not enable a user dotenv.

Importing a [config section](#config-sections) registers it on `APP_RC`.
The [config CLI](#configuration-tools) reads that same declaration to determine
which settings and commands to expose. Defining a setting once therefore makes
it available to loading, diagnostics, and editing.

## Config sections

A config section is a class of related settings. The starter's
[`AppSettings`](../src/{my_project}/config/sections/app.py) contains `storage_root`
and `message`. Each `rc.field(...)` connects a Python attribute to an environment
key and supplies its default and help text.

`message` is a string with a Python fallback. The packaged dotenv also supplies
its initial value. `storage_root` is a required `Path` populated from the selected
storage; it is not an editable preference. [Adding a setting](How-To-User-Guides.md#add-a-setting)
means adding a field to this section, or adding a focused section for another
part of the application.

Field `title`, `explanation_short`, and `explanation_long` are reused by the
config editor. Use `secret=True` for redacted display of sensitive values; this
flag does not encrypt stored values.

## ResolvedConfig

A `ResolvedConfig` contains the values read for one invocation. The mounted CLI
calls `APP_RC.resolve()` and stores the result as `state.resolved`.
`resolved.build({MyProject}Config)` converts those inputs into the application's
[config bundle](#config-bundle).

For example, `{MY_PROJECT}_MESSAGE=hello` supplies a string to the `message`
field. Each result retains the values it read. Selecting another storage for a
later run does not change an earlier result or mutate `os.environ`.
The [application-code guide](How-To-User-Guides.md#use-settings-in-application-code)
shows how to construct settings explicitly outside the CLI.

## Configuration files

The starter reads configuration layers in increasing priority: Python defaults,
packaged defaults, selected storage's dotenv, explicit dotenv files, and process
environment. A later value replaces an earlier value for the same key.

For example, `message` can be `Hello from {my_project}` in
[`apprc.defaults.env`](../src/{my_project}/config/apprc.defaults.env), `work` in the
storage dotenv, and `temporary` in the process environment. The application
uses `temporary`. The [precedence example](EXAMPLES.md#an-invocation-override)
shows this with commands. Provenance records which source supplied each field.

The AppRC directory defaults to `~/.local/share/{my_project}`.
`{MY_PROJECT}_APPRC_DIR` relocates it. It contains the storage registry and, if
user overrides are later enabled, `apprc.user.env`. It is separate from the
installed Python package and can be separate from the storage directories.
[References](References.md#configuration-files) lists the exact filenames.

## Storage

A storage is a directory for the application's persistent data. Its
`apprc.storage.env` supplies settings specific to that directory. AppRC registers
and manages the directory; application code writes its own data using the
selected root path.

The storage registry is `apprc.toml` in the AppRC directory. It maps names to
paths and remembers a default. An invocation can select another name with
`--storage NAME`, while `config storage select NAME` changes the saved default
for later runs. [Switching storage](How-To-User-Guides.md#switch-storage) shows both.

The generated CLI explicitly requires selected storage for runtime commands.
Help, setup, and diagnostics remain usable before setup. A
[storage-only application](EXAMPLES.md#storage-only-application) is the starter's
complete setup. The [user-preferences example](EXAMPLES.md#user-preferences-and-storage)
adds a shared user layer beneath storage-specific settings.

## Configuration tools

`APP_RC.manage()` returns a `ConfigManager` that initializes files, inspects
settings, plans edits, and manages storages. It provides the same operations to
Python code and the interactive interfaces. Creating a manager does not write.

The config CLI is the `config` command group mounted on Typer. `config doctor`
reports missing values and source problems; `config set` saves an override;
`config edit` opens the Textual config editor. The
[editing guide](How-To-User-Guides.md#edit-a-saved-setting) shows which file changes.

The config editor displays effective values and their contributing layers. It
can edit saved user or storage overrides, but it does not rewrite packaged
defaults or the parent shell's environment. Opening it writes nothing; setup and
save are explicit actions. Terminal setup exists today. Toga and native installer
integrations are future AppRC work and are not generated by this scaffold.

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

`apprc>=0.25.0,<0.26` provides configuration and the terminal dependencies.
`apprc` installs the matching `apprc-core`; Typer is also a direct dependency
because application code imports it. Test and maintainer tools belong to the
`dev` dependency group. [Dependency declarations](References.md#dependency-declarations)
state where to add each kind of requirement.
