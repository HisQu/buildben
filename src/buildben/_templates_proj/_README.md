

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
   1. [Install a release](#install-a-release)
   2. [Install from a checkout](#install-from-a-checkout)
   3. [Uninstall](#uninstall)
3. [Usage](#usage)
   1. [Use Feature X](#use-feature-x)
   2. [Use Feature Y](#use-feature-y)
4. [Documentation](#documentation)


---

<!-- ====================================================================== -->
<br>

# Installation

The installer uses Python 3.12 or newer through `uv`. If `uv` is not available,
it installs the official user-scoped `uv` executable and lets `uv` provision a
compatible Python; no system Python or administrator access is required.

<br>

## Install a release

The generated release-mode native entry can run by itself. It acquires and
verifies the matching source and release manifest; adjacent manifest and
`main-installer.py` files are not required. Downloading the complete release
asset set is an optional workflow when you want to inspect or retain those
assets locally.

```shell
gh release download vX.Y.Z --repo <github_username>/<my_project>
./app-install.sh
```

On Windows, run the downloaded `app-install.cmd` instead:

```powershell
gh release download vX.Y.Z --repo <github_username>/<my_project>
.\app-install.cmd
```

The default source selection installs the pinned source archive. `--version
X.Y.Z` selects a specific published release, and `--main` resolves the
repository's current `main` to one immutable commit for that invocation. These
choices cannot be combined. `--github-client gh` selects authenticated GitHub
CLI downloads; public downloads do not inherit GitHub CLI credentials. Private
VCS dependencies separately require Git credentials. Windows installation
does not require administrator privileges.

For a source checkout, first generate its local AppRC artifacts with
`just make-artifacts`, then use `./app-install.sh` or `.\app-install.cmd`.
`just check-artifacts` verifies tracked output without rewriting it. A missing
checkout payload reports the generation command; it never fetches a replacement
from a remote repository.

The installer offers native or single-root resource placement when the
application declares resource capabilities. Use `--layout native` for native
locations or `--layout single-root --root ABSOLUTE_PATH` for a single root.
Reinstallation keeps the saved absolute placement unless an explicit layout
override is supplied. Buildben itself declares no application data paths.

Configuration setup is optional and does not block installation management.

<br>

## Install from a checkout

Clone the repository, synchronize its locked authoring environment, and
generate local AppRC artifacts before running the checkout installer:

```shell
git clone https://github.com/<github_username>/<my_project>.git
cd <my_project>
uv sync --locked --all-extras --all-groups
just make-artifacts
```

On Linux and macOS, run:

```shell
./app-install.sh --layout native
{my_project} launcher
```

On Windows, run:

```powershell
.\app-install.cmd --layout native
{my_project} launcher
```

The checkout install is editable and uses the actual project files, including
uncommitted changes. It does not alter the repository's saved source revision.
Use `just check-artifacts` to check generated outputs without rewriting them.

<br>

## Uninstall

Run `./app-uninstall.sh` on Linux or macOS, or `.\app-uninstall.cmd` on Windows.
The default removes the managed program and retains declared resources and
installation recovery support. Complete removal requires an explicit request:

```shell
./app-uninstall.sh --complete --category config --category appdata --yes
```

Use the same options with `app-uninstall.cmd` on Windows. Only select resource
categories that the application declared; unknown files and external data are
not inferred as cleanup targets. The saved uninstall code invokes any
repository-owned cleanup before removing the installed program. Inspection and
recovery use `{my_project} installation show`, `{my_project} installation
doctor`, and `{my_project} installation repair`.

The saved controller is stored under the fixed native `installation/` address,
separate from application data. Repeated commands do not redirect it when the
shell's `HOME`, XDG variables, or `LOCALAPPDATA` change.

<br>


<!-- ====================================================================== -->
<br>


# Usage

The installed command and AppRC management remain available before business
setup. Run these commands from the installed application environment:

```shell
{my_project} version
{my_project} diagnose --json
{my_project} installation show
{my_project} config show --json
{my_project} launcher
```

Application resources use the paths declared by `APP_RC`. Config, appdata,
cache, and state are independent capabilities; disabled paths stay absent and
installation management does not enable them. The `installation/` authority is
separate from application data. See the
[filesystem capabilities](docs/Explanations.md#filesystem-capabilities) and
[installation placement reference](docs/References.md#installation-placement).



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
    - [Unix installer staging verification](docs/Development.md#unix-installer-staging-verification)
    - [Releases](docs/Development.md#releases)

