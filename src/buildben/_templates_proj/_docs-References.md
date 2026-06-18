<!-- ======================================================== -->
## Table Of Contents
<!-- ======================================================== -->

1. [References](#1-references)
2. [Project Reference](#2-project-reference)
   1. [Project Paths](#project-paths)
   2. [Command Reference](#command-reference)
   3. [Dependency Surfaces](#dependency-surfaces)
   4. [Environment Variables](#environment-variables)
   5. [Configuration Files](#configuration-files)
   6. [Public Interfaces](#public-interfaces)
   7. [Figure Visual Tokens](#figure-visual-tokens)

<br>

# 1. References

Use this file when you need an exact path, command, environment variable, or
public name. Use [How-To User Guides](How-To-User-Guides.md) for procedure and
[Explanations](Explanations.md) for concepts.

<br>

# 2. Project Reference

<!-- ======================================================== -->
## Project Paths
<!-- ======================================================== -->

Core paths:

| Path | Role |
|---|---|
| [README.IGNORE.md](../README.IGNORE.md) | Short setup entry point. Rename to `README.md` when the project is ready to publish. |
| [AGENTS.md](../AGENTS.md) | Local coding and documentation guidance for agents. |
| [pyproject.toml](../pyproject.toml) | Package metadata, dependencies, and tool configuration. |
| [justfile](../justfile) | Development commands. |
| [src/{my_project}](../src/{my_project}) | Runtime package source. |
| [tests](../tests) | Test suite. |
| [examples](../examples) | Small user-facing examples. |
| [assets](../assets) | Project assets. |
| [docs](.) | Long-form project documentation. |

> [!NOTE]
> Related: use [Development: repository routing](Development.md#repository-routing)
> before adding files or moving behavior between directories.

<br>

<!-- ======================================================== -->
## Command Reference
<!-- ======================================================== -->

Common commands:

| Command | Role |
|---|---|
| `just --list` | Show available development recipes. |
| `just sync` | Sync the full maintainer environment from `uv.lock`. |
| `python -m pip install -e "."` | Install runtime package dependencies without `uv`. |
| `python -m pip install -e "." --group dev` | Install maintainer tools without `uv`. |
| `{my_project} --help` | Show the console command tree. |
| `{my_project} version` | Print the installed package version. |
| `{my_project} diagnose` | Print local package and Python diagnostics. |
| `{my_project} config setup --yes --storage-root STORAGE_ROOT` | Create first-run single-storage AppRC setup. |
| `{my_project} config doctor` | Check AppRC storage setup. |
| `{my_project} config init STORAGE_ROOT --name NAME` | Register a multi-storage root after `{MY_PROJECT}_APPRC_TOML` is exported. |
| `{my_project} config list` | List AppRC multi-storage registrations. |
| `{my_project} config show --json` | Show resolved runtime config metadata. |
| `{my_project} config edit` | Open the AppRC Textual config editor. |
| `python -m {my_project} --help` | Smoke-test the module entry point. |
| `ruff format .` | Format Python files. |
| `ruff check .` | Lint Python files. |
| `pyright` | Type-check Python files. |
| `python -m pytest` | Run the test suite. |

> [!NOTE]
> Related: use [How-To User Guides: run tests](How-To-User-Guides.md#run-tests)
> for the command sequence.

<br>

<!-- ======================================================== -->
## Dependency Surfaces
<!-- ======================================================== -->

Dependency locations:

| Surface | File Section | Use |
|---|---|---|
| Runtime dependencies | `[project].dependencies` | Packages required by normal users. |
| Optional feature extras | `[project.optional-dependencies]` | Published extras for optional runtime features. |
| Dependency groups | `[dependency-groups]` | Local maintainer tools such as tests, linting, typing, docs, and profiling. |
| Lock file | `uv.lock` | Reproducible `uv` installs. |

> [!NOTE]
> Related: use [dependency model](Explanations.md#dependency-model) for why
> optional runtime features and maintainer-only tools stay separate.

<br>

<!-- ======================================================== -->
## Environment Variables
<!-- ======================================================== -->

Common environment variables:

| Name | Role |
|---|---|
| `{MY_PROJECT}_STORAGE` | Active storage selector, usually a storage-root path in single-storage mode. |
| `{MY_PROJECT}_APPRC_TOML` | Optional AppRC TOML file for named multi-storage workflows. |
| `{MY_PROJECT}_MESSAGE` | Starter example setting loaded from `config/.env.shared` or local storage. |
| `VIRTUAL_ENV` | Active virtual environment path. |
| `PYTHONPATH` | Import-path override for local smoke tests. Prefer editable installs for normal development. |
| `UV_PROJECT_ENVIRONMENT` | Optional `uv` virtual environment path override. |

> [!NOTE]
> Related: use [How-To User Guides: environment problems](How-To-User-Guides.md#environment-problems)
> for the first checks when imports resolve from the wrong location.

<br>

<!-- ======================================================== -->
## Configuration Files
<!-- ======================================================== -->

Important config files:

| File | Role |
|---|---|
| [pyproject.toml](../pyproject.toml) | Python packaging, dependencies, and tool settings. |
| [src/{my_project}/config/.env.shared](../src/{my_project}/config/.env.shared) | Packaged AppRC defaults loaded before local and shell overrides. |
| `{MY_PROJECT}_APPRC_TOML -> <path>/{my_project}.apprc.toml` | Optional AppRC TOML file for named multi-storage roots. |
| `<storage-root>/.env.local` | Storage-local AppRC overrides written by `{my_project} config set`. |
| [.envrc](../.envrc) | `direnv` integration. |
| [.gitignore](../.gitignore) | Local and generated files excluded from Git. |
| [.github/workflows_inactive](../.github/workflows_inactive) | Inactive starter CI workflows. |

> [!NOTE]
> Related: use [configuration model](Explanations.md#configuration-model) for
> how local settings, environment variables, and package defaults should stay
> understandable.

<br>

<!-- ======================================================== -->
## Public Interfaces
<!-- ======================================================== -->

Document public surfaces here as the project grows:

| Surface | Current Name | Stability |
|---|---|---|
| Package import | `{my_project}` | Public once README examples use it. |
| Console script | `{my_project}` | Public command declared in `pyproject.toml`. |
| Module entrypoint | `python -m {my_project}` | Public module execution path. |
| CLI app owner | `{my_project}.cli.app` | Command tree implementation owner. |
| Entrypoint wrapper | `{my_project}.main` | Thin wrapper for package metadata entry points. |
| Config owner specs | `{my_project}.config.owners` | App-owned AppRC field inventory. |
| Config facade | `{my_project}.config.APP_CONFIG` | AppRC kit used by CLI bootstrap and config commands. |

> [!NOTE]
> Related: use [How-To User Guides: run the first command](How-To-User-Guides.md#run-the-first-command)
> for the first user-facing smoke test.

<br>

<!-- ======================================================== -->
## Figure Visual Tokens
<!-- ======================================================== -->

Graphigs owns the figure theme, token names, and rendered color swatches. Keep
figure captions and generated asset names stable here, but do not duplicate
rendered theme swatches in this repository.

> [!NOTE]
> Related links:
> - Use [Graphigs Theme](https://github.com/markur4/graphigs/blob/main/docs/Theme.md)
>   for current figure token values and swatches.
> - Use [static figure rules](Development.md#static-figure-rules) before adding docs figures.
> - Use [documentation authoring](Development.md#documentation-authoring) before changing docs structure or figure assets.
