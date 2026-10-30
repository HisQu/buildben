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
| `{my_project} installation migrate --dry-run` | Preview recognized legacy migration without writes. |
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

Release preparation uses `just check-artifacts`, builds one validated wheel
and sdist, then runs `just stage-release-assets TAG FULL_COMMIT`. The helper
stages only the exact package pair and SDK-generated script entries in
`release/assets` and delegates manifest creation to the strict release asset
contract. Package builds do not generate artifacts or access the network.

## Uninstaller reference

`app-uninstall.sh` and `app-uninstall.cmd` route through the repository-authored
uninstall module and saved AppRC controller. The default retains declared
application resources and installation recovery support. Complete removal
requires an explicit category selection and confirmation:

| Option | Effect |
| --- | --- |
| `--complete` | Request complete removal of selected, recorded resources. |
| `--category config\|appdata\|cache\|state` | Select one owned resource category; repeat as needed. |
| `--forget-retained` | Explicitly leave and report retained files where supported. |
| `--yes` | Confirm the requested uninstall without an interactive prompt. |

The saved controller is kept under the fixed native
`installation/` directory, separate from appdata. Inspection and recovery use
`{my_project} installation show`, `{my_project} installation doctor`, and
`{my_project} installation repair`; these management commands do not require
business settings to resolve.

Project-specific cleanup belongs in ordinary repository functions called while
the program remains installed. Cleanup that cannot prove ownership keeps the
affected resource and installation authority for recovery. Unknown descendants,
external workspaces, shared uv, and shared Python are not inferred as removal
targets.

## Installation placement

The installer supports `native` paths or one explicit `single-root` layout.
`--layout` and `--root` are installer options; `--root` is valid only with
`--layout single-root` and must be absolute. The saved placement records enabled
resource paths, which reinstallation reuses by default. This resource layout is
separate from the program environment: `uv tool install` manages the application
program in its tool environment, while `--layout` selects declared application
resource locations. Changing layout does not move the installed program or
automatically move existing resource contents.


The legacy Buildben receipt is recognized only at
`%LOCALAPPDATA%/<normalized-distribution>/installation/receipt.json` on Windows
or `${XDG_STATE_HOME:-~/.local/state}/<normalized-distribution>/installation/receipt.json`
on POSIX. To cut it over, first stop legacy installers, launchers, and
uninstallers. Then explicitly choose a layout, provide verified installed-source
evidence, and confirm quiescence:

```sh
./app-install.sh --migrate-legacy --legacy-quiescent --legacy-source legacy-source.json --layout native
./app-install.sh --migrate-legacy --legacy-quiescent --legacy-source legacy-source.json --layout single-root --root ABSOLUTE_PATH
```

Use `app-install.cmd` for Windows. The cutover validates the recorded uv
backend and known helper files; unknown files block migration and remain
untouched until reviewed. If a durable migration is interrupted, the installer
resumes that recorded migration on its next run. Preflight conflicts must be
resolved before repeating the explicit migration command.

`--legacy-source` is a JSON file with exactly `source` and
`distribution_record_digest`. `source` contains the SDK's complete
`InstallationSource` fields: `kind`, `requirement`, `version`, `digest`,
`runtime_requirements`, and `runtime_overrides`. Without `--reinstall-legacy`,
use the actual original acquisition and installed observation, not the current
checkout or a newer release. Nullable fields remain JSON `null`; requirement
lists remain arrays. The SDK checks the recorded backend and legacy version
before cutover. Original wheel/release/materialized-main adoption needs its
verified archive digest and installed RECORD fingerprint; a version label is
not source proof. With `--reinstall-legacy`, `source` instead selects a verified
immutable replacement and the required RECORD digest still identifies the old
installed program. This is explicit input, not a second discovery receipt.

For example, a previously observed editable source can be represented as:

```json
{
  "source": {
    "kind": "editable",
    "requirement": "/absolute/original/project",
    "version": null,
    "digest": null,
    "runtime_requirements": [],
    "runtime_overrides": []
  },
  "distribution_record_digest": null
}
```

Only use that example for a genuinely editable legacy installation, with its
actual recorded constraints and overrides. An old receipt that records only a
release label does not prove the original archive bytes or installed origin.
If that evidence is unavailable, use explicit verified replacement below rather
than silently adopting this checkout. Once replacement is journaled, retry uses
the saved source/backend/support rather than asking for a new source choice;
fresh `--legacy-quiescent` confirmation is still required.

To collect the installed metadata without importing old business configuration,
use the final SDK's ordinary metadata probe with the **recorded tool
environment's interpreter**, not the `python` entry in the old receipt (that
may be an external base interpreter):

```sh
probe="$(uv run --locked python -c 'from apprc.distribution.runtime import installed_probe; print(installed_probe.__file__)')"
"/absolute/recorded/tool-dir/<normalized-distribution>/bin/python" "$probe" \
  --distribution "<normalized-distribution>" \
  --app-id "<actual-app-id>" \
  --import-package "<my_project>" \
  --command "<my_project>" > legacy-observation.json
```

On Windows, use the recorded tool environment's `Scripts/python.exe` with the
same probe path and arguments. Add one `--command` for each actual installed
entry point. This produces `version`, `direct_url`, and
`distribution_record_digest` from that environment. Match `version` to
`receipt.json`; copy the observed RECORD digest into the evidence file rather
than hashing a different checkout. The cutover runs this probe again and
compares the result, so collecting metadata does not authorize adoption.

For adoption without `--reinstall-legacy`, use original verified inputs for `source`.
An editable PEP 610 `direct_url` must name the original absolute project and have
`dir_info.editable=true`. A VCS source must retain the actual credential-free
GitHub repository, complete commit, and subdirectory from its `vcs_info` and
`subdirectory` fields; represent it as an `index` requirement
`git+https://github.com/OWNER/REPO.git@FULL_COMMIT#subdirectory=PROJECT_PATH`.
Use the observed installed version, not this checkout's version. For an SDK
content-addressed wheel or release source, obtain the original archive SHA-256,
source locator, constraints, and overrides from the verified acquisition
manifest or retained artifact; the installed observation alone does not
reconstruct those original inputs.

There is a further strict SDK boundary: noneditable wheel/release origins
must use its content-addressed staging convention, independently checked
against the supplied archive digest and installed RECORD fingerprint. A legacy
release installed from an arbitrary old temporary directory cannot be adopted
by renaming its provenance to the current checkout or inventing a digest.
To replace such an installation from a verified immutable source, use:

```sh
./app-install.sh --migrate-legacy --reinstall-legacy --legacy-quiescent \
  --legacy-source legacy-source.json --layout native
```

Choose an immutable wheel/release archive or full-commit source and its verified
digest; provide the independently observed **old** RECORD fingerprint. This
reinstalls the Python program but does not move data or workspaces. The exact
recorded interpreter/backend is reused. Durable pending authority precedes the
backend change, and old controllers retire only after strict replacement proof.
After interruption, stop old processes again and rerun the matching command
with `--legacy-quiescent`; the pending source remains authoritative even if the
original temporary directory or source-evidence file is no longer available.

Config, appdata, cache, and state are independent declared capabilities.
Disabled paths remain absent; an installation record does not enable appdata.
The fixed native `installation/` directory is separate from these purgeable
resources and remains available for inspection and recovery.

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
