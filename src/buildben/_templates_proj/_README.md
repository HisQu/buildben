

<!-- This is a comment -->

<!-- ============================================================== -->
<!-- == Header ==================================================== -->
<div align="center">

<!-- --- Title ---------------------------------------------------- -->
# `{my_project}`: A Template


<!-- --- Logo ----------------------------------------------------- -->
*Part of:*

<a href="https://hisqu.de" target="_blank">
  <img 
  src="https://avatars.githubusercontent.com/u/196629600?s=200&v=4" 
  width="100px" alt="logo"
  style="margin-top: -10px;"> 
</a>

<br>

<!-- --- Badges --------------------------------------------------- -->
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/type%20checked-pyright-blue)](https://microsoft.github.io/pyright/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC)](https://docs.pytest.org/)
<!-- [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/HisQu/haiu/blob/main/LICENSE) -->




</div>

<!-- --- URLs --------------------------------------------------- -->
[`direnv`]: https://direnv.net/
[`just`]: https://github.com/casey/just?tab=readme-ov-file#packages
[`uv`]: https://github.com/astral-sh/uv?tab=readme-ov-file#uv


<!-- ============================================================== -->
<!-- ============================================================== -->

<div style="width: 85%; margin: 2rem auto; text-align: justify;">
<hr>

###  `{my_project}` ...
<!-- Replace this starter description when the application has its own purpose. -->
A Python command-line application with typed settings and named directories for
persistent data. AppRC supplies configuration commands and a terminal editor.


#### Main dependencies:
<!-- List your main dependencies here and explain why they're important. -->
- **`apprc`**: Runtime config, generated `config` CLI, and Textual editor.

<hr>
</div>


<!-- Graphical Abstract goes here: -->

<!-- | ![Graphical abstract](./assets/figures/graphical-abstract_init-proj-graphviz.svg) |
|:--:|
| **Fig. 1 - Graphical Abstract:** Buildben creates scaffolds for Python projects adhering to Python PEP standards. |

<br> -->

<!-- HTML-version of Graphical Abstract -->
<!-- 
<div align="center">
  <img src="https://github.com/HisQu/buildben/raw/main/assets/figures/diagram-graphviz.svg"
       width="800px" alt="Management of Virtual Environments & Dependencies" >
  <p><em> 
  <b> Graphical Abstract: </b> 
  Management of Virtual Environments & Dependencies. Red dashed lines are Dependencies.
  </em></p>
</div> 




-->




<!-- ============================================================== -->
<!-- ============================================================== -->
## Table of contents

- [Installation](#installation)
  - [One-line install](#one-line-install)
  - [Install from a cloned repository](#install-from-a-cloned-repository)
  - [Remove an installation](#remove-an-installation)
- [Usage](#usage)
- [Development](#development)
- [Documentation](#documentation)

## Installation

Use Python 3.12 or newer.

### One-line install

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

### Install from a cloned repository

Clone the repository and install it with Python and pip. This workflow does not
require uv:

```shell
git clone https://github.com/<github_username>/<my_project>.git
cd <my_project>
```

#### For Linux & macOS

```shell
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/{my_project} config setup
.venv/bin/{my_project} --help
```

#### For Windows

```powershell
py -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e .
& '.\.venv\Scripts\{my_project}.exe' config setup
& '.\.venv\Scripts\{my_project}.exe' --help
```



### Remove an installation

For a one-line installation, remove the application with
`uv tool uninstall {my_project}`. For an editable install from a cloned
repository, run `.venv/bin/python -m pip uninstall {my_project}` on Linux or
macOS, or `& '.\.venv\Scripts\python.exe' -m pip uninstall {my_project}` in
Windows PowerShell. Remove the clone and its `.venv` when you no longer need
them.

If the one-line installer also installed uv in the default directory, remove
its executables:

Linux and macOS:

```shell
rm -f ~/.local/bin/uv ~/.local/bin/uvx ~/.local/bin/uvw
```

Windows PowerShell:

```powershell
Remove-Item -ErrorAction SilentlyContinue "$HOME\.local\bin\uv.exe", "$HOME\.local\bin\uvx.exe", "$HOME\.local\bin\uvw.exe"
```

See Astral's [uv uninstallation guide](https://docs.astral.sh/uv/getting-started/installation/#uninstallation)
for other install locations and optional data cleanup.

## Usage

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

## Development

Install maintainer tools with pip 25.1 or newer:

```shell
python -m pip install -e "." --group dev
python -m pytest
```

[Development](docs/Development.md) covers verification, optional extras, locks,
and releases. The [config-section guide](docs/How-To-User-Guides.md#add-a-setting)
shows where to add a setting and its help text.

## Documentation

| Page | Contents |
| --- | --- |
| [Documentation](docs/README.md) | Reading order, component names, and writing rules. |
| [Explanations](docs/Explanations.md) | Components and how they connect. |
| [How-to user guides](docs/How-To-User-Guides.md) | Tasks with prerequisites and expected results. |
| [References](docs/References.md) | Exact commands, paths, keys, and Python names. |
| [Examples](docs/EXAMPLES.md) | Complete storage, override, and multi-section examples. |
| [Development](docs/Development.md) | Maintainer setup and release workflow. |
