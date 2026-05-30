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
| `PROJECT_ROOT` | Optional project-root override used by helper code when implemented. |
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
| [.env.template](../.env.template) | Example environment variables. |
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
| Config attributes | None yet. | Add exact names before documenting workflows that rely on them. |

> [!NOTE]
> Related: use [How-To User Guides: run the first command](How-To-User-Guides.md#run-the-first-command)
> for the first user-facing smoke test.

<br>

<!-- ======================================================== -->
## Figure Visual Tokens
<!-- ======================================================== -->

Use these role-based tokens for docs diagrams and static figures. Keep the
token names stable when a figure source script exists so generated assets and
Markdown references stay easy to compare.

Typography tokens:

| Token | Value | Role |
|---|---|---|
| `FONT` | `sans-serif` | Default figure font. |
| `MONO_FONT` | `monospace` | Monospace figure font for paths, commands, and code-like labels. |
| `NODE_FONT_SIZE` | `DOC_FIGURE_LEGIBILITY.node_font_pt` | Node and card body text size. |
| `EDGE_FONT_SIZE` | `DOC_FIGURE_LEGIBILITY.edge_font_pt` | Edge text size. |
| `EDGE_LABEL_FONT_SIZE` | `9.5` | Compact edge label text size. |
| `TITLE_FONT_SIZE` | `DOC_FIGURE_LEGIBILITY.title_font_pt` | Figure title text size. |
| `FONT_SIZE` | `NODE_FONT_SIZE` | Alias for the default node body text size. |

Text and stroke tokens:

| Token | Hex | Preview | Role |
|---|---|---|---|
| `BLACK` | `#000000` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#000000;"></span> | Neutral black primitive. |
| `NEUTRAL_STROKE` | `#666666` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#666666;"></span> | Neutral outline and edge primitive. |
| `TEXT_COLOR` | `#000000` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#000000;"></span> | Figure text color; aliases `BLACK`. |
| `INVERTED_TEXT_COLOR` | `#ffffff` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#ffffff;"></span> | Text color for dark filled shapes. |
| `NODE_STROKE` | `#666666` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#666666;"></span> | Node and card outlines; aliases `NEUTRAL_STROKE`. |
| `EDGE_STROKE` | `#666666` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#666666;"></span> | Edges and connectors; aliases `NEUTRAL_STROKE`. |

Readable surface tokens:

| Token | Hex | Preview | Role |
|---|---|---|---|
| `NODE_SURFACE_FILL` | `#f4f4f4dd` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f4f4f4dd;"></span> | Readable node and card body fill. |
| `CLASSIFIER_SURFACE_FILL` | `#f4f4f4dd` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f4f4f4dd;"></span> | Classifier body fill; aliases `NODE_SURFACE_FILL`. |
| `TEXT_BOX_SURFACE_FILL` | `#f4f4f4dd` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f4f4f4dd;"></span> | Text-box body fill; aliases `NODE_SURFACE_FILL`. |

Grouping surface tokens:

| Token | Hex | Preview | Role |
|---|---|---|---|
| `NEUTRAL_GROUP_FILL` | `#44444419` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#44444419;"></span> | Translucent neutral grouping region. |
| `LEGEND_GROUP_FILL` | `#f4f4f499` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f4f4f499;"></span> | Translucent legend grouping region. |

Semantic color tokens:

| Token | Hex | Preview | Role |
|---|---|---|---|
| `OLIVE` | `#afb200ff` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#afb200ff;"></span> | Olive semantic color. |
| `OLIVE_GROUP_FILL` | `#afb20019` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#afb20019;"></span> | Translucent olive grouping region. |
| `BLUE` | `#00A2FF` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#00A2FF;"></span> | Blue semantic color. |
| `BLUE_GROUP_FILL` | `#00A2FF19` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#00A2FF19;"></span> | Translucent blue grouping region. |
| `GREEN` | `#32bc00ff` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#32bc00ff;"></span> | Green semantic color. |
| `GREEN_GROUP_FILL` | `#32bc0019` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#32bc0019;"></span> | Translucent green grouping region. |
| `ORANGE` | `#f4a261ff` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f4a261ff;"></span> | Orange semantic color. |
| `ORANGE_GROUP_FILL` | `#f4a26119` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f4a26119;"></span> | Translucent orange grouping region. |
| `PURPLE` | `#8b5cf6ff` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#8b5cf6ff;"></span> | Purple semantic color. |
| `PURPLE_GROUP_FILL` | `#8b5cf619` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#8b5cf619;"></span> | Translucent purple grouping region. |
| `TEAL` | `#00a6a6ff` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#00a6a6ff;"></span> | Teal semantic color. |
| `TEAL_GROUP_FILL` | `#00a6a619` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#00a6a619;"></span> | Translucent teal grouping region. |
| `RED` | `#EE220C` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#EE220C;"></span> | Red semantic color. |
| `RED_GROUP_FILL` | `#EE220C19` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#EE220C19;"></span> | Translucent red grouping region. |
| `STANDARDS_GROUP_FILL` | `#f27f72dc` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#f27f72dc;"></span> | Standards grouping region. |

Classifier icon colors:

| Kind | Icon | Hex | Preview | Role |
|---|---|---|---|---|
| `actor` | `A` | `#A9DCDF` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#A9DCDF;"></span> | Actor classifier icon fill. |
| `class` | `C` | `#ADD1B2` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#ADD1B2;"></span> | Class classifier icon fill. |
| `interface` | `I` | `#B4A7E5` | <span style="display:inline-block;width:1.25em;height:1.25em;border:1px solid #666666;background-color:#B4A7E5;"></span> | Interface classifier icon fill. |

> [!NOTE]
> Related links:
> - Use [static figure rules](README.md#static-figure-rules) before adding docs figures.
> - Use [documentation authoring](Development.md#documentation-authoring) before changing docs structure or figure assets.
