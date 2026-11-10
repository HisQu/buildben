<!-- ============================================================== -->
<!-- == Header ==================================================== -->
<div align="center">

<!-- --- Title ---------------------------------------------------- -->

# `buildben`: build-benedictions

*Part of:*
<!-- --- Logo ----------------------------------------------------- -->
<a href="https://hisqu.de" target="_blank">
  <img src="https://avatars.githubusercontent.com/u/196629600?s=200&v=4" 
       width="100px" alt="logo" style="margin-top: -10px;">
</a>

<br>

<!-- --- Badges --------------------------------------------------- -->

[![Code style:
black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

<!-- ============================================================== -->
<!-- == Abstract ================================================== -->
<div style="width: 85%; margin: 2rem auto; text-align: justify;">
<hr>

<blockquote> <i> A <b> benediction </b>(Latin: bene, 'well' + dicere, 'to speak') is a short invocation for divine help, blessing and guidance, usually at the end of worship service. </i> <sup> <a href="https://en.wikipedia.org/wiki/Benediction"> Wikipedia </a></sup> </blockquote>


#### `buildben` ...
<!-- Summarize the top 3 features -->
- ... = a Python development tool.
- ... standardizes project & experiment setups with template scaffolds
- ... integrates popular tools like `pipx`, `direnv`, `just`, etc.
- ... snapshots a project commit, lock file, and build artifacts for reproducible experiments


#### Main dependencies:
<!-- List your main dependencies here and explain why they're important. -->
- **[`uv`](https://github.com/astral-sh/uv)**: Awesome fast dependency manager & virtual environment tool, etc.
- **[`direnv`](https://direnv.net/)**: Auto-loads project-specific environment and provides  one-liners for environment management.
- **[`just`](https://github.com/casey/just)**: For running tasks to manage build tools & the virtual environment.

<!-- Dev dependencies: 
- **[`pipx`](https://pipx.pypa.io)**: The recommended home for `buildben`, making it accessible globally while keeping the OS-Python clean
- **Dependency groups:** Local dev tools live in `[dependency-groups]` and install with `python -m pip install -e "." --group dev`.
-->

<hr>
</div>
  



<!-- <div align="center">
<img src="./assets/figures/graphical-abstract_init-proj-graphviz.svg" alt="graphical-abstract_init-proj-graphviz.png" width="600px" style="background-color:transparent">
  <p>
  <b> Graphical Abstract</b>: Buildben creates scaffolds for python projects adhering to Python PEP-standards.
  </p>
</div> -->




| ![Graphical abstract](./assets/figures/graphical-abstract_init-proj-graphviz.svg) |
|:--:|
| **Fig. 1 - Graphical Abstract:** Buildben creates scaffolds for Python projects adhering to Python PEP standards. |

<br>



### Table of Contents

<!-- toc -->

1. [`buildben`: build-benedictions](#buildben-build-benedictions)
   1. [📦 Installation](#-installation)
      1. [Native installer entries](#native-installer-entries)
      1. [Authoring lifecycle artifacts](#authoring-lifecycle-artifacts)
      1. [Windows installer verification procedure](#windows-installer-verification-procedure)
      1. [Unix installer staging verification](#unix-installer-staging-verification)
      1. [Uninstall](#uninstall)
   2. [🚀 Usage](#-usage)
   3. [❓Optional Installs](#optional-installs)
   4. [📚  Examples / Documentation](#--examples--documentation)

<!-- tocstop -->
<!-- /toc -->

<br>

<!-- ============================================================== -->
<!-- == Installation ============================================== -->
## 📦 Installation

### Prerequisites

Editable pip installation needs Python `>=3.12` and a virtual environment.
The native installer can provision uv/Python without administrator privileges;
it does not require the application or AppRC to be installed first. Network
access is needed for selected sources, Python and unresolved dependencies.

### 🏃Quick & Dirty:
```bash
git clone https://github.com/HisQu/buildben.git
cd buildben
python -m pip install -e "."    # venv recommended
```

### Native installer entries

> [!IMPORTANT]
> This checkout prepares Buildben 0.12 and AppRC 0.31; changing the source version
> does not publish either package. Until a matching Buildben release exists, use
> the checkout entries below rather than expecting new assets in an older release.
> The committed immutable AppRC source pins bridge the unpublished dependency.

From a complete checkout, run the local project entry:

```sh
./app-install.sh
```

```powershell
.\app-install.cmd
```

This installs the actual editable application project, including dirty local
changes. It does not archive `HEAD` or silently replace missing local payload
with downloaded code. If tracked artifacts are missing/stale, the author runs
`just make-artifacts`; CI uses `just check-artifacts` without rewriting.
Ordinary `python -m pip install -e .` remains supported and unmanaged by this
uv-tool lifecycle.

Once matching release assets have been published, the explicitly release-mode
native entry is usable by itself. Download it into a separate working directory:

```sh
curl -fL --output app-install.sh \
  https://github.com/HisQu/buildben/releases/latest/download/app-install.sh
chmod u+x app-install.sh
./app-install.sh
```

```powershell
Invoke-WebRequest -Uri 'https://github.com/HisQu/buildben/releases/latest/download/app-install.cmd' -OutFile app-install.cmd
.\app-install.cmd
```

Release mode selects one matching installer/package identity and validates its
manifest and exact source digest. It must not independently combine a newer
installer with an older package. A raw checkout wrapper is not a standalone
release asset: downloading just that wrapper cannot supply its local payload.

| Selection | Installer behavior |
| --- | --- |
| Complete checkout, no source override | Install the actual local project editable. |
| Release-native entry, no source override | Install the latest published stable source distribution. |
| `--version X.Y.Z` | Install the selected published stable release. |
| `--main` | Resolve remote main once and install that captured commit's matching source/runtime inputs. |

`--main` cannot be combined with `--version`; it requires GitHub access and may
select unreleased code. The installer reports the captured source commit, since
the package version alone may also identify a release. Public access uses
anonymous requests. For authenticated access use `--github-client gh` after
`gh auth login` and `gh auth setup-git`; curl does not inherit gh credentials,
and private VCS dependencies still need Git authentication.

For an AppRC application, first installation offers OS-native versus single-root
placement, displays exact enabled resource paths, and explains the distinction:

- **Application resources:** config, persistent appdata, disposable cache and
  operational state, only when individually declared by the application.
- **Program environment:** Python, the uv-managed virtual environment and its
  dependencies. Choosing an application root does not relocate these.
- **Installation metadata:** durable support at a fixed native address, outside
  a chosen single root and outside disposable state.

Reinstallation keeps saved placement unless explicitly switched:

```sh
./app-install.sh --layout native
./app-install.sh --layout single-root --root "/absolute/path/application-files"
```

```powershell
.\app-install.cmd --layout single-root --root 'D:\ApplicationFiles'
```

`--root` is valid only with single-root and must be absolute; native accepts no
root. A switch preserves previous owned resource locations as retired targets;
it does not automatically move arbitrary databases or user projects. Invocation
layout controls and `apprc.defaults.env` are not persistence for installer choices.

Buildben itself declares no AppRC data capabilities and has no AppRC runtime
dependency. It therefore creates no config/appdata/cache/state resource roots.
Its durable `installation.json` and current-platform support use:

| OS | Buildben installation directory |
| --- | --- |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/buildben/installation` |
| macOS | `~/Library/Application Support/buildben/installation` |
| Windows | `%LOCALAPPDATA%\buildben\installation` |

The source generator lives in `src/buildben_distr/`; generated applications own
the corresponding `<app>_distr` package. Its ordinary-Python payload controls
project setup/cleanup while reusing AppRC's shared runtime. Run `app-launch.sh`
or `app-launch.cmd` to invoke saved application launch support; launch never
installs/syncs an environment. Buildben launches its direct CLI, while generated
AppRC applications expose their installed Textual `launcher` command.

### Authoring lifecycle artifacts

Keep project-specific prerequisites and cleanup in
`src/<app>_distr/payload/app_lifecycle/`; keep distribution identity and composition
in `src/<app>_distr/make_artifacts.py`. These are authoring inputs, not another
installed application package or an alternative lifecycle engine.

After changing those inputs:

```sh
uv sync --locked --all-groups
just make-artifacts
just check-artifacts
```

Commit the authored inputs and their generated outputs together. `check-artifacts`
compares expected bytes without rewriting them. Neither package build hooks nor
an end user's launch should regenerate artifacts or fetch missing checkout code.

The artifact authoring and staging recipes select the locked project environment
through uv. They do not require an activated virtual environment or direnv.

Before publication, the development sources and tool-install runtime overrides
must point to the same immutable AppRC commit; a uv development source alone
does not control the installed application's dependencies.

Generated AppRC applications group management commands in the **Maintenance**
help panel instead of mixing them with business commands. Use `<app> --help`,
`<app> installation show --json`, `<app> installation doctor`, and
`<app> installation uninstall --dry-run` for inspection; `<app> launcher` opens
the installed Textual launcher. These management entrypoints must remain usable
when business configuration is missing. Buildben itself keeps its direct CLI
and does not acquire an AppRC runtime dependency merely to provide installation.

### Windows installer verification procedure

Use the existing `windows-latest` matrix in the
[`installation` CI job](.github/workflows/ci.yml) for native Windows evidence.
Extend the existing [release-install tests](tests/test_release_install.py),
not copied installer functions or a separate harness. Exercise the real
installer through the native `.cmd` entry and PowerShell helper, including file
execution with `-File` and downloaded-text `ScriptBlock.Create` invocation.

On the native Windows runner, run:

```powershell
uv run --locked python -m pytest -n 0 tests/test_release_install.py -k windows_installer
```

The source-install consumer smoke must also complete through
[`just release-install-smoke`](justfile), which checks real source installation
and saved uninstallation through both Windows entrypoints. Focused tests alone
do not replace that smoke. Linux checks are useful but do not prove Windows
installation or behavior.

> [!WARNING]
> From WSL, never launch native Windows verification executables: PowerShell,
> Windows Python/pytest, `cmd.exe`, or Windows `uv`, directly or through helpers.
> Do not use a cross-OS virtual environment as a workaround. Previous local
> attempts terminated the terminal; the cause is unknown. Output capture,
> `-NoProfile`, and `-NonInteractive` do not establish console isolation, and
> `CREATE_NO_WINDOW` is not a proven fix. Do not retry locally.

A separately authorized, independent native Windows runner is an alternative;
this WSL terminal is not. Observe CI runs with Linux `gh` and record the actual
run and results; configured CI is not evidence that a run completed. If permissions,
billing, or secrets block CI, record the concrete blocker and leave Windows proof
and release readiness pending. Main-branch integration normally waits for that
proof, but an explicit user decision may authorize merge/push with the native
gap clearly recorded. That override does not make Linux results Windows evidence
or authorize a release. Do not change billing, policy, or security settings or
publish artifacts to bypass the blocker. Pushes still require explicit authorization.

### Unix installer staging verification

Run [`just release-install-smoke`](justfile) after changing Unix staging.
The maintained [consumer tests](tests/test_release_install.py) exercise release
and pinned-main sources through both the canonical installer and the Unix
installer rendered by the real scaffolder. Cover physical and symlinked
temporary parents, actual installation, saved uninstallation, and cleanup.
The existing macOS `installation` jobs must execute successfully before release;
main integration with that native gap requires the same explicit user override
described in the [Windows procedure](#windows-installer-verification-procedure).

Normalize only the newly created installer-owned staging root before deriving
extracted-source paths. A macOS system alias such as `/var` must not make valid
staging fail lifecycle validation. Do not resolve arbitrary lifecycle or
preflight inputs to bypass their link checks; keep the rejection coverage in
[`tests/test_lifecycle.py`](tests/test_lifecycle.py).

Generated-consumer cases must invoke the real scaffolder and AppRC generator,
then install that consumer's own source—not reuse Buildben as a stand-in.
Keep both kinds of evidence: canonical Buildben exercises a zero-data
application, while generated applications exercise declared resources and
project-specific setup/cleanup alongside the shared lifecycle.

### Uninstall

Installer-based installations save inspection/removal support outside the
removable application environment. Use the native path printed by installation,
or dispatch through the complete checkout:

```sh
./app-uninstall.sh --dry-run
./app-uninstall.sh --yes
```

```powershell
.\app-uninstall.cmd --dry-run
.\app-uninstall.cmd --yes
```

Default removal is **program-only**. It verifies actual backend absence, retains
reconnectable placement/support and records `removed-retained`, not a fictitious
installed version. For generated applications it retains every config/appdata/
cache/state resource. Buildben has none. Editable checkout files, workspaces,
shared uv/Python, shell configuration and unrelated tools are never implicit
removal targets. There is no inherited legacy `--remove-uv` permission.

Complete removal is separate. Buildben's zero-resource example removes its
remaining owned support/authority after confirming the preview:

```sh
./app-uninstall.sh --dry-run --complete
./app-uninstall.sh --complete --yes
```

Generated applications additionally select exact owned resource categories with
repeatable `--category config|appdata|cache|state`. Persistent config/appdata
deletion needs explicit consent; `--yes` does not bypass ownership, unknown-file,
revision or generation checks. `--forget-retained` names retained files in its
preview and deliberately leaves them unmanaged; it never means they were deleted.

Saved inspection/dry-run is read-only: no uv bootstrap, downloads, environment
creation or resource initialization. It needs an already available suitable
Python; otherwise it reports that prerequisite. Mutating removal may provision
its pinned management dependencies through uv, but uses the saved app-specific
procedure instead of downloading newer cleanup code. Keep the recorded uv/base
Python available. The independent controller waits for the actual caller and its
owned foreground children to exit before deleting the environment.

Incomplete work retains progress and a matching saved/external recovery command.
Unknown contents and provider failures retain authority rather than claiming
complete deletion. Complete removal deletes `installation.json` last; afterward
only lock retirement and empty-container cleanup may occur. Safe lock residue
under contention is reported, not used as permission to delete a new generation.

Existing legacy `receipt.json` installations require explicit migration. Stop old
installers, launchers and uninstallers first, then use the complete checkout:

```sh
./app-install.sh --migrate-legacy --legacy-quiescent \
  --legacy-source legacy-source.json --layout native
```

Use `app-install.cmd` on Windows. The first cutover needs the explicit layout and
source evidence; a journaled interruption resumes from the durable migration.
Known Windows in-place or old POSIX state-directory support is inspected, and
known old runnable entries are retired before new authority becomes active.
Unknown files are not adopted.

`legacy-source.json` has exactly `source` and `distribution_record_digest`.
The source contains `kind`, `requirement`, `version`, `digest`,
`runtime_requirements` and `runtime_overrides`, using the actual original
acquisition and observed installed metadata—not this checkout or a guessed hash.
The installer re-probes the recorded backend and compares the legacy version and
required installed `RECORD` fingerprint. See the [source-evidence collection
procedure](src/buildben/_templates_proj/_docs-References.md) for the SDK metadata
probe and exact JSON shape; replace the scaffold's example identities with
`buildben` and its actual `buildben`/`bube` commands.

For old noneditable installs whose arbitrary temporary source has been deleted,
do not invent original provenance. Explicitly reinstall from a verified immutable
source before cutover:

```sh
./app-install.sh --migrate-legacy --reinstall-legacy --legacy-quiescent \
  --legacy-source legacy-source.json --layout native
```

In this mode, `source` selects the verified replacement; the RECORD digest still
describes the **old installed program**. This replaces its uv-managed program
environment, not user data or workspaces. The recorded interpreter/backend is
preserved, and old controllers retire only after the replacement is observed.
After an interruption, stop old processes again and retry the matching command
with `--legacy-quiescent`; pending authority supplies the saved source and paths.
Reinstallation is never an automatic fallback from failed adoption.

For an unmanaged editable pip installation, use that environment's
`python -m pip uninstall buildben`. For a manually installed uv tool without
managed authority, use `uv tool uninstall buildben` with its original
`UV_TOOL_DIR`/`UV_TOOL_BIN_DIR`; do not fabricate a receipt or treat another
environment discovered on PATH as its owner.


### Install from a cloned repository


#### 3. Install [`just`](https://github.com/casey/just):
```bash
sudo apt install just     # For Ubuntu
# brew install just       # For MacOS
# pipx install rust-just  # Windows requires the cross-platform version (not tested!)
```


#### 4. Install [`direnv`](https://direnv.net/) & hook it into your shell: 
   - *Either* follow the instructions for [install](https://direnv.net/docs/installation.html) & [hook](https://direnv.net/docs/hook.html),
   - *Or* run `src/buildben/setup_zsh.sh` to install both `zsh` & other useful plugins, including `direnv`.

```bash
# === Example for Ubuntu + zsh =============
sudo apt install direnv
# Add direnv plugin (or just the hook) if missing
RCFILE="${ZDOTDIR:-$HOME}/.zshrc" # Respect ZDOTDIR if user set it
if ! grep -q 'direnv ' "$RCFILE"; then
    sed -i 's/^plugins=(/plugins=(direnv /' "$RCFILE"
fi
```


### ✅ Verify installation:
```bash
bube        # Prints help when no args are given
# buildben  # Alias for bube
```

<br>




<!-- ============================================================== -->
<!-- == Usage ===================================================== -->
## 🚀 Usage

### Projects


<div align="center">
<img src="./assets/figures/diagram-graphviz.svg" alt="diagram-graphviz.svg" width="1000px" style="background-color:transparent">
  <p><em> 
  <b> Architecture of projects </b>
  </em></p>
</div>


```bash
# Initialize project scaffold:
bube init-proj \   # Long Alias for `bube proj`
  -n my_project \  # Project name = Name of new project folder
  -t . \           # Parent directory to place new project folder into
  -u your_github_username
  -g               # Initializes git repo and commits scaffold
```

The generated project includes six documentation pages. They use fixed page
labels and introduce components before instructions that depend on them:

- `docs/README.md`: Documentation, the reading order and authoring rules.
- `docs/Explanations.md`: Explanations, each component's job and connections.
- `docs/How-To-User-Guides.md`: How-to user guides, tasks with prerequisites and expected results.
- `docs/References.md`: References, exact commands, paths, keys, and Python names.
- `docs/EXAMPLES.md`: Examples, complete storage and configuration setups.
- `docs/Development.md`: Development, verification and release instructions.

The root `CONTRIBUTING.md` owns shared working conventions and the normal
development setup and checks; `AGENTS.md` directs coding agents to those rules.
The generated README provides grouped navigation for users and contributors
instead of duplicating development commands.

Generated projects also include `.github/workflows/diagnostics.yml`, an isolated
Actions artifact upload/download check requiring no checkout or Python setup.
The generated [developer guide](src/buildben/_templates_proj/_docs-Development.md#actions-artifact-diagnostic)
explains the initial `diagnostics/artifact-upload` branch push, later manual
invocation, and deletion of the tiny test artifact (one-day fallback retention).
It checks Actions artifact storage, not GitHub Release uploads, PyPI publication,
or application correctness.

The starter has a Typer CLI, `python -m <my_project>` support, and AppRC
configuration. It enables named storage without a user dotenv. One `APP_RC`
declaration registers typed sections; a config bundle passes those sections to
application code. The `config` commands initialize storage, edit settings, and
open the terminal editor. The generated docs and `AGENTS.md` require consistent
component names and links inside the paragraphs and tables where they are useful.

> [!IMPORTANT]
> Generated projects require `apprc>=0.29.0,<0.30` and its matching `apprc-core`.
> Buildben itself still has no runtime dependencies. Existing projects are not
> rewritten automatically.

To verify generated projects with that dependency available, run
`uv run --locked --with 'apprc>=0.29.0,<0.30' python -m pytest`.
For local AppRC changes, install matching locally built `apprc-core` and `apprc`
wheels, set `APPRC_ARTIFACTS` to their directory, and use
`UV_FIND_LINKS="$APPRC_ARTIFACTS"` for generated consumer installs. Local wheel
paths belong in the verification environment, not production requirements.
Missing AppRC is an unmet verification prerequisite; skipped generated-runtime
checks do not establish compatibility.

#### Create virtual environment (``/.direnv``):

```bash
cd <my_project_name> # Changing directory will auto-create the venv
# ==> You will be prompted to allow the direnv to activate!
# direnv allow
```

#### Install dependency profiles:
```bash
python -m pip install -e "."              # Core runtime dependencies
python -m pip install -e ".[rag]"         # Core + published RAG extra
python -m pip install -e "." --group dev  # Core + local dev tools
python -m pip install -e ".[rag]" --group dev
```
The `rag` commands apply after the commented `rag` extra in `pyproject.toml` is
uncommented and populated.
<details> <summary> Equivalent uv / just commands </summary>

  - `just core`: `uv sync --locked --no-default-groups`
  - `just rag`: `uv sync --locked --all-extras --no-default-groups`
  - `just dev`: `uv sync --locked --all-groups`
  - `just rag-dev`: `uv sync --locked --all-extras --all-groups`
  - `--all-extras` installs published extras from `[project.optional-dependencies]`, such as `rag`.
  - `--all-groups` installs local dependency groups from `[dependency-groups]`, such as `dev`.
  - `--no-default-groups` skips uv's default local groups for a runtime-only install.

</details>

#### List `just` recipes:
*Recipes* (=functions) are defined in the `justfile`. Edit them or add more as you like! 
`just --list` displays recipes grouped by task.
```bash
just  # Alias for `just --list`. 
```

#### 'Uninstall' Project:
```bash
rm -rf ../my_project  # Simply delete the project folder
```

<hr>


### Experiments
Experiments are defined as scripts meant to use, test, validate, etc.
your current project. They will be collected inside the `experiments`
directory inside the project root, including templates for Reports, outputs, etc.!

```bash
# From inside your project:
bube add-experim experiment1 # Alias: `bube exp experiment1`
# > Creates the scaffold in `./experiments/2025-06-13_experiment1`
```

<hr>

### Snapshots
You can create a snapshot of your current project, sparing you the
headache of PyPI releases and semantic versioning. This is useful for
e.g. reproducing your experiment after the project has changed. It works by
capturing the current commit hash, exporting locked requirements with `uv`,
and building local wheel/sdist artifacts.
```bash
# From inside your project:
bube env-snapshot experiments/2025-06-13_experiment1
# > Creates experiment.env, requirements.lock, wheel, and sdist artifacts
```

### Maintainer releases

Buildben keeps its PyPI policy in the `justfile`:

```just
RELEASE_PYPI := "false"
```

Keep it at `"false"` for GitHub-only releases. Set it to `"true"` once for a
public package after configuring PyPI trusted publishing for the `pypi` GitHub
environment.

> [!IMPORTANT]
> Edit and commit this setting before the release. Shell variables and
> `just --set` overrides are not stored in the tag and cannot select PyPI.

```bash
just release-check
just release patch
```
`just build-release-inputs` accepts an optional positional release-notes path:

```bash
just build-release-inputs release/prepared-notes.md
```

Use this to reuse notes that have already been validated. The file must be
outside `dist`, because the recipe rebuilds that directory. Omit the argument
to generate notes from the changelog; either way, tag and version validation
still runs.

> [!WARNING]
> `just release` creates the version commit and annotated tag, then atomically
> pushes `main` and the tag. Use `just release-prepare patch` when you only want
> the checked local commit and tag.

Manual PyPI publication is available only when both the current committed
`justfile` and the target tag's committed `justfile` set
`RELEASE_PYPI := "true"`. If a GitHub Release exists and that policy is true,
publish its attached wheel and source archive without rebuilding them:

```bash
just publish-pypi vMAJOR.MINOR.PATCH
```

The command checks both committed policies before GitHub authentication or
network calls. When either policy is `"false"`, it exits without contacting
GitHub. The manual workflow applies the same check to the selected workflow ref
and target tag. When both are true, its unprivileged preflight validates the
Release assets, records their hashes and release/tag/commit identities in a
manifest, and uploads that exact snapshot. The PyPI job publishes only the
snapshot identified by the preflight artifact ID.

The preflight detects a tag update or deletion during asset capture. Preventing
an administrator from changing or deleting the tag while preflight is running
requires repository tag protection or rulesets. This code does not configure
or verify those settings. GitHub Actions performs an allowed PyPI upload
through trusted publishing.


<br>



<!-- ============================================================== -->
<!-- == Optionals ================================================= -->

## ❓Optional Installs

### Use `direnv` & `just` in VS Code:

#### Select Python Interpreter:
This needs to be repeated for every new workspace folder!
1. Press ``Ctrl + Shift + P``; search & select *"Python: Select Interpreter"*
2. It will list workspace folders. Select the one you want to assign the direnv-interpreter to.
3. It will list available interpreters `.direnv/python-3.x.y` should be next to the global ones (VS Code documentation claims it knows `direnv` out-of-the-box!).
4. If it does not appear, then try adding this to your ``settings.json`` & replace ``<path_to_your_projects>`` with the actual parent folder where you store your projects. It must be within your home directory, and VS Code must have permission to that folder!


```json
// Optional: Patterns inside the home directory that point to a parent folder containing a venv or python-3.x.y:
  "python.venvFolders": [ "user/<path_to_your_projects>/*/.direnv" ],
```
5. You might also try activating "python.terminal.activateEnvironment" in the VS Code settings.


#### Install VS Code Extensions:
```bash
code --install-extension mkhl.direnv 
code --install-extension nefrob.vscode-just
```

<br>

### [`Mermaid`](https://mermaid.js.org/) - For Quick & Dirty Diagrams

#### Install VS Code Extension:
```bash
code --install-extension vstirbu.vscode-mermaid-preview
```
``Mermaid`` runs natively in GitHub & Markdown-tools.


### [`graphigs`](https://github.com/markur4/graphigs) - For Big Figures

Buildben owns the source for repository figures in `assets/figures`, beside the
generated SVG and PNG files. The scripts import `graphigs` for shared Graphviz
helpers, size checks, and SVG/PNG export normalization.

#### Install the system layout engine:

```bash
sudo apt-get install graphviz              # For Ubuntu
# brew install graphviz                    # For MacOS
# winget install -e --id Graphviz.Graphviz # Windows
```

#### Render the repository figures:

```bash
just figures
# or run one colocated renderer:
uv run --locked python assets/figures/diagram_graphviz.py
```

New project scaffolds copy flowchart and class diagram starters from Graphigs.
After installing Graphigs in the maintainer environment, refresh the snapshots
with `PYTHONPATH=src python -m buildben_dev.sync_mermaid_templates`. Add
`--check` to report stale snapshots without writing files.
<br>




<!-- ============================================================== -->
<!-- == Examples ================================================== -->


## 📚  Examples / Documentation 

### Diagrams

| **Feature**       | **``Mermaid``**                                         | **``Graphviz``**                                                   |
| ----------------- | --------------------------------------------------- | -------------------------------------------------------------- |
| **Ease of Use**   | 🟢 Simple, Markdown-like syntax; quick to learn and use  | 🟡 DOT-based layout with Python helper scripts |
| **Integration**   | 🟢 Native to GitHub and Markdown-tools, no extra installs      | 🟡 Requires the Graphviz system package |
| **Functionality** | 🔴 Limited styling and diagram types                     | 🟢 Strong graph layout, SVG/PNG export, reusable styling helpers |






#### `Mermaid`  flowchart (code inside `README.md`):

```mermaid
flowchart LR
    %% Nodes
        A("fab:fa-youtube Starter Guide")
        B("fab:fa-youtube Make Flowchart")
        n1@{ icon: "fa:gem", pos: "b", h: 24}
        C("fa:fa-book-open Learn More")
        D{"Use the editor"}
        n2(Many shapes)@{ shape: delay}
        E(fa:fa-shapes Visual Editor)
        F("fa:fa-chevron-up Add node in toolbar")
        G("fa:fa-comment-dots AI chat")
        H("fa:fa-arrow-left Open AI in side menu")
        I("fa:fa-code Text")
        J(fa:fa-arrow-left Type Mermaid syntax)

    %% Edge connections between nodes
        A <--> B --> C --> n1 & D & n2
        D -- Build and Design --> E --> F
        D -- Use AI --> G --> H
        D -- Mermaid js --> I --> J

    %% Individual node styling. Try the visual editor toolbar for easier styling!
        style E color:#FFFFFF, fill:#AA00FF, stroke:#AA00FF
        style G color:#FFFFFF, stroke:#00C853, fill:#00C853
        style I color:#FFFFFF, stroke:#2962FF, fill:#2962FF
```

####  `Mermaid`  Class Diagram (code inside `README.md`):
```mermaid
classDiagram 
direction LR
  
  %% Class Mammals
  class Heart {
    // Organ
    -health: float
    -beat() -> None
  }
  
  class Leg {
    // Body part
    +walk() -> None
  }
  <<Interface>> Leg
  
  class Mammal {
    -heart: Heart
    +leg: tuple[Leg]
  }
  <<Abstract>> Mammal
  
  %% Class Humans
  class Arm {
    // Body part
  }
  <<Interface>> Arm
  
  class Clothes {
    +type: str
  }
  
  class Human {
    // Mammal
    +arm: tuple[Arm]
    +clothes: Clothes
  }
  
  %% Edge connections
  Heart --* Mammal : "1" (composition)
  Leg --* Mammal : "2 or 4" (composition)


  Mammal <|-- Human : (is a)
  Arm --* Human : "2" (composition)
  Clothes --o Human : "0..*" (aggregation)

```
