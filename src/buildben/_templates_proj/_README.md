

<!-- README EDITING CONTRACT
Adapt this README in place. Preserve its structure, HTML layout, heading levels,
spacing, and useful content. Replace placeholders and update facts within this
design. Before editing, read "README maintenance" in CONTRIBUTING.md.
-->


<!-- ====================================================================== -->
<!-- --- URLs  -->
[`direnv`]: https://direnv.net/
[`just`]: https://github.com/casey/just?tab=readme-ov-file#packages
[`uv`]: https://github.com/astral-sh/uv?tab=readme-ov-file#uv
[`apprc`]: https://pypi.org/project/apprc/




<!-- ====================================================================== -->
<!-- == Header -->
<div align="center">


<!-- --- Title  -->
<a id="project-overview"></a>

# `{my_project}`: A Template


<!-- --- Logo  -->
 <!-- *Part of:*

<a href="https://hisqu.de" target="_blank">
  <img 
  src="https://avatars.githubusercontent.com/u/196629600?s=200&v=4" 
  width="100px" alt="logo"
  style="margin-top: -10px;"> 
</a> 

<br> -->



<!-- --- Badges -->

[![CI](https://github.com/<github_username>/<my_project>/actions/workflows/ci.yml/badge.svg)](https://github.com/<github_username>/<my_project>/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](pyproject.toml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/<distribution_name>)](https://pypi.org/project/<distribution_name>/)


[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/type%20checked-pyright-blue)](https://microsoft.github.io/pyright/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC)](https://docs.pytest.org/)


</div>



<!-- --- Abstract  -->


A Python command-line application with typed settings and named directories for
persistent data. AppRC supplies configuration commands and a terminal editor.


#### Main dependencies:
<!-- List your main dependencies here and explain why they're important. -->
- **[`apprc`]**: Runtime config, generated `config` CLI, and Textual editor.




<!-- --- Graphical Abstract  -->

<br>

<!-- | ![Graphical abstract](./assets/figures/graphical-abstract_init-proj-graphviz.svg) |
|:--:|
| **Fig. 1 - Graphical Abstract:** Buildben creates scaffolds for Python projects adhering to Python PEP standards. |

<br>  -->


<!-- HTML-version of Graphical Abstract -->
<!-- 

<br>

<div align="center">
  <img src="https://github.com/HisQu/buildben/raw/main/assets/figures/diagram-graphviz.svg"
       width="800px" alt="Management of Virtual Environments & Dependencies" >
  <p><em> 
  <b> Graphical Abstract: </b> 
  Management of Virtual Environments & Dependencies. Red dashed lines are Dependencies.
  </em></p>
</div> 



 -->


<br>

---




<!-- ====================================================================== -->
### Table of Contents

1. [`{my_project}`: A Template](#project-overview)
2. [Installation](#installation)
   1. [One-Line Install](#one-line-install)
   2. [Install from a Cloned Repository](#install-from-a-cloned-repository)
   3. [Uninstall](#uninstall)
3. [Usage](#usage)
   1. [First-Time Use](#first-time-use)
   2. [Use Feature X](#use-feature-x)
   3. [Use Feature Y](#use-feature-y)
4. [Documentation](#documentation)

---

<!-- ====================================================================== -->
<br>

# Installation

Use Python 3.12 or newer.

<br>

## One-Line Install

The installer bootstraps from the current `main` branch in both modes. By
default it installs the latest stable release source distribution; append
`--version X.Y.Z` to select a specific stable release. Release installation
uses the published release artifact. `--main` instead installs one snapshot of
the current remote `main`, pinned to the commit resolved for that invocation
and its committed `uv.lock`; it does not install local or uncommitted checkout
changes, and requires no GitHub release or Actions artifact.

`--main` requires GitHub access. Public access uses anonymous HTTPS; authenticated
access uses GitHub CLI and requires the setup below. Main may contain unreleased
code whose CI has not passed. The installed version comes from `pyproject.toml`
and may match a release; the installer prints the source commit SHA to identify
the snapshot. Omit `--main`, or use `--version`, to install a release again.
`--main` and `--version` cannot be combined.

| Selection | Installer behavior |
| --- | --- |
| *(no source option)* | Install the latest published stable source archive. |
| `--version X.Y.Z` | Install the selected published stable release. |
| `--main` | Install one captured commit from remote `main` with its committed `uv.lock`. |

For authenticated access, install [GitHub CLI](https://cli.github.com/), then run
`gh auth login` and `gh auth setup-git`. Pass `--github-client gh` to use it;
public downloads and curl do not inherit gh credentials. Private VCS
dependencies independently require Git credentials. Windows installation does
not require administrator privileges.

Public and authenticated installer commands for Linux, macOS, and Windows are
shown below for reference; the examples remain commented out.

<!--
#### For Linux & macOS

```shell
installer="$(curl -fsSL 'https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-linux-macos.sh')" && test -n "$installer" && bash -c "$installer" --
```

```shell
installer="$(gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-linux-macos.sh')" && test -n "$installer" && bash -c "$installer" -- --github-client gh
```

#### For Windows

```powershell
$url = 'https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-windows.ps1'; $s = Invoke-RestMethod -Uri $url; if ([string]::IsNullOrWhiteSpace(($s -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($s -join "`n")))
```

```powershell
$s = gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-windows.ps1'; if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($s -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($s -join "`n"))) '--github-client' 'gh'
```
```shell
installer="$(curl -fsSL 'https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-linux-macos.sh')" && test -n "$installer" && bash -c "$installer" -- --main
```

```shell
installer="$(gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-linux-macos.sh')" && test -n "$installer" && bash -c "$installer" -- --github-client gh --main
```

```powershell
$url = 'https://raw.githubusercontent.com/<github_username>/<my_project>/main/src/<my_project>_dev/distribution/install-windows.ps1'; $s = Invoke-RestMethod -Uri $url; if ([string]::IsNullOrWhiteSpace(($s -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($s -join "`n"))) '--main'
```

```powershell
$s = gh api -H 'Accept: application/vnd.github.raw+json' 'repos/<github_username>/<my_project>/contents/src/<my_project>_dev/distribution/install-windows.ps1'; if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($s -join "`n"))) { throw 'Could not download the installer.' }; & ([scriptblock]::Create(($s -join "`n"))) '--github-client' 'gh' '--main'
```
-->

After installation, the installer runs `{my_project} config setup`, which guides
you through initial configuration.

<br>

## Install from a Cloned Repository

Clone the repository and install it with Python and pip. This workflow does not
require uv:

```shell
git clone https://github.com/<github_username>/<my_project>.git
cd <my_project>
```

### For Linux & macOS

```shell
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/{my_project} config setup
.venv/bin/{my_project} --help
```

### For Windows

```powershell
py -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e .
& '.\.venv\Scripts\{my_project}.exe' config setup
& '.\.venv\Scripts\{my_project}.exe' --help
```

<br>

## Uninstall

For a one-line installation, run the saved native uninstaller printed during
installation. The checkout shortcuts `./uninstall.sh` and `.\uninstall.cmd`
dispatch to that same offline helper. Start with `--dry-run`; use `--yes` to
confirm package removal without a terminal. Data and uv are kept by default.

The helper lives outside the removable tool environment at
`${XDG_STATE_HOME:-$HOME/.local/state}/<distribution_name>/installation` on Unix
or `%LOCALAPPDATA%\<distribution_name>\installation` on Windows. Unix
`XDG_STATE_HOME` must be absolute; Windows requires `LOCALAPPDATA`.
It uses the recorded base Python 3.12+ interpreter, which must remain available.
The helper and receipt survive removal so repeated invocation remains safe.
The saved helper keeps its own package-removal receipt even if a later shell
changes `XDG_STATE_HOME` or `LOCALAPPDATA`.

To inspect and explicitly clean AppRC-managed data before removal:

```shell
{my_project} appdata paths --json
{my_project} appdata clean --dry-run
./uninstall.sh --clean-appdata --yes
```

On Windows use `.\uninstall.cmd --clean-appdata --yes`. `--yes` alone never
consents to cleanup or uv removal. `--apprc-dir PATH` explicitly selects the
managed directory for cleanup. Cleanup retains external payloads and unmanaged
data, and stops removal if its preview or application command fails. The helper
rejects cleanup targets that would delete its saved recovery support.

`--remove-uv` requests a separate, conservative ownership check and confirmation.
Even an empty tool inventory does not prove other projects no longer use uv.
See the [removal guide](docs/How-To-User-Guides.md#remove-an-installation) for
eligibility, legacy recovery, and editable pip installations, and the
[uninstaller reference](docs/References.md#uninstaller-reference) for all options.


<!-- ====================================================================== -->
<br>


# Usage

Before using first, time, config with. 


<br>

## First-Time Use

The starter reads typed settings and manages a directory for persistent data.
This POSIX example keeps that data next to the checkout:

```shell
export {MY_PROJECT}_APPRC_DIR="$PWD/.demo-config"
{my_project} version
{my_project} diagnose --json
{my_project} config setup --yes --storage-root ../{my_project}-data
{my_project} config doctor
{my_project} config set app.message "Hello local storage" --scope storage
{my_project} config show --json
```

With `{MY_PROJECT}_MESSAGE` unset, the output includes `Hello local storage`.
The [storage explanation](docs/Explanations.md#storage) describes where data and
settings live. Open `{my_project} config edit` to inspect and edit settings in
the terminal, or [register another storage](docs/How-To-User-Guides.md#switch-storage).



<br>

## Use Feature X

<!-- Explain core feature after setup -->

lorem ipsum dolor


<br>

## Use Feature Y

<!-- Explain core feature after setup -->

lorem ipsum




<!-- ====================================================================== -->
<br>

# Documentation

- **Using the project**
  - [Documentation](docs/README.md) — Start here and find the right guide.
  - [How-to user guides](docs/How-To-User-Guides.md) — Complete specific tasks.
  - [Examples](docs/EXAMPLES.md) — Follow complete, working examples.
  - [Explanations](docs/Explanations.md) — Understand the components and their connections.
  - [References](docs/References.md) — Look up commands, settings, and APIs.

- **Contributing and maintaining**
  - [Contributing](CONTRIBUTING.md) — Propose changes and prepare a contribution.
  - [Development](docs/Development.md) — Work on the code and maintain the project.
    - [Development environment](docs/Development.md#maintainer-environment)
    - [Repository layout](docs/Development.md#repository-routing)
    - [Documentation authoring](docs/Development.md#documentation-authoring)
    - [Verification](docs/Development.md#verification)
    - [Windows installer verification](docs/Development.md#windows-installer-verification-procedure)
    - [Releases](docs/Development.md#releases)

