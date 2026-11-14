

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

The managed application environment uses Python 3.13, selected by
`tool.apprc.distribution.runtime-python` in `pyproject.toml`. This is separate
from `project.requires-python`, which describes package-install compatibility
(the scaffold defaults to `>=3.12`). PyApp's bootstrap uses Python 3.14; it does
not determine the Python version used by the installed application.

<br>

## Install a release

Download the native setup for the current platform together with `SHA256SUMS`:

```shell
gh release download vX.Y.Z --repo <github_username>/<my_project>
./<my_project>-setup-linux-x86_64
```

On Windows, run `<my_project>-setup-windows-x86_64.exe`. The checksum file
covers exactly those two setup executables. Windows cross-compilation is not
Windows runtime validation.

## Install from a checkout

From the intended checkout, prepare its existing environment with the committed
lock and register the editable application:

```shell
uv sync --locked --all-extras --all-groups
uv run --locked <my_project> app install -e
```

Editable registration reuses this checkout and its `.venv`; it does not resolve
dependencies, copy source, or create an environment. Use `uv sync --locked` to
restore a broken development environment. `just make-artifacts` builds native
setups from the committed Git revision (defaults to `HEAD`); it does not capture
uncommitted changes. `just check-artifacts` validates declarations and final
setup checksums without rebuilding or writing.

For React projects, `just build-python-packages` builds the wheel and sdist from
the same committed, locked source snapshot used by native authoring. Bun runs
only on the private copy; generated `_web/` files and build intermediates do not
modify the checkout. The Python packages are staged in
`.cache/apprc/python-packages/`, separately from native setup files in `dist/`.

The setup executable performs a managed install of the embedded committed
project snapshot. Use `app install -e` only from an intended source checkout.
Application resource placement is recorded and reused on reinstall.

## Uninstall

Use `{my_project} app uninstall --dry-run` to inspect removal and
`{my_project} app uninstall --yes` to remove the program while retaining
declared resources. Explicitly select resource categories for deletion; unknown
files and external checkouts are never inferred as cleanup targets.

The installation record and recovery support are stored separately from
application data. Changing HOME, XDG variables, or LOCALAPPDATA later does not
redirect an existing installation.

<br>


<!-- ====================================================================== -->
<br>


# Usage

The installed command and AppRC management remain available before business
setup:

```shell
<my_project> version
<my_project> paths --json
<my_project> app doctor
<my_project> config show --json
<my_project> launch
```

Application resources use the paths declared by `APP_RC`; installation
management does not enable undeclared capabilities. See the
[filesystem capabilities](docs/Explanations.md#filesystem-capabilities) and
[installation placement reference](docs/References.md#installation-placement).


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

### Using the Project
- [Documentation](docs/README.md) — Start here and find the right guide.
- [How-to user guides](docs/How-To-User-Guides.md) — Complete specific tasks.
- [Examples](docs/EXAMPLES.md) — Follow complete, working examples.
- [Explanations](docs/Explanations.md) — Understand the components and their connections.
- [References](docs/References.md) — Look up commands, settings, and APIs.

### Contributing and Maintaining
- [Contributing](CONTRIBUTING.md) — Propose changes and prepare a contribution.
- [Development](docs/Development.md) — Work on the code and maintain the project.
  - [Development environment](docs/Development.md#maintainer-environment)
  - [Repository layout](docs/Development.md#repository-routing)
  - [Documentation authoring](docs/Development.md#documentation-authoring)
  - [Verification](docs/Development.md#verification)
  - [Windows installer verification](docs/Development.md#windows-installer-verification-procedure)
  - [Unix installer staging verification](docs/Development.md#unix-installer-staging-verification)
  - [Releases](docs/Development.md#releases)

