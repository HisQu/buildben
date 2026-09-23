# Development

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Examples](EXAMPLES.md)

- [Maintainer environment](#maintainer-environment)
- [Repository routing](#repository-routing)
- [Before editing](#before-editing)
- [Documentation authoring](#documentation-authoring)
- [Static figure rules](#static-figure-rules)
- [Verification](#verification)
- [Releases](#releases)

## Maintainer environment

From the project root, install the package and development tools with Python
3.12 or newer. The `--group` option requires pip 25.1 or newer:

```shell
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e "." --group dev
```

On Windows use `.venv\Scripts\python.exe`. With uv, use `just sync` after
[creating the lock files](#releases). `uv`, `direnv`, and `just` are optional for
application users. The [dependency reference](References.md#dependency-declarations)
distinguishes installed requirements from maintainer tools.

The starter has no enabled optional extras. If you add and populate the
commented `rag` extra in `pyproject.toml`, these commands install it:

```shell
python -m pip install -e ".[rag]"
python -m pip install -e ".[rag]" --group dev
```

## Repository routing

| Change | Location |
| --- | --- |
| Runtime behavior | `src/{my_project}` |
| Commands | `src/{my_project}/cli/app.py` |
| Settings | `src/{my_project}/config/sections` |
| Tests | `tests` |
| Small user-facing programs | `examples` |
| Documentation | `docs` |
| Release and build helpers | `src/{my_project}_dev/packaging` |
| Static assets | `assets` or `docs/assets` |

The [project paths](References.md#project-paths) table links to existing owners.
Ask before adding a top-level directory when one of these locations fits.
Keep package initializers limited to imports and module docstrings. Reuse
existing helpers, use exact attributes on known types, and write Sphinx-style
docstrings for public behavior.

## Before editing

Read [AGENTS.md](../AGENTS.md), [TODO.md](../TODO.md), and the relevant component
in [Explanations](Explanations.md). Inspect `git status --short` and nearby
source before editing. Keep unrelated user changes untouched. Explain the
intended change before editing several files.

Update docs when setup, commands, APIs, environment variables, or saved file
formats change. Record the final behavior in [CHANGELOG.md](../CHANGELOG.md),
including affected users and migration instructions for breaking changes.

## Documentation authoring

Follow the [documentation rules](README.md#documentation-rules) and
[component names](README.md#component-names). They define the names used across
all six pages. An explanation must identify a component, explain its job and
connections, and link the relevant words to a working implementation.

Write from the smallest usable configuration to optional features. Introduce a
term before using it in a task title. Keep exact API names and filenames. Link
inside the sentence or table cell where a reader needs the information; do not
append generic further-reading lists or related-link callouts. References must
connect commands and fields to their explanations and practical examples.

Give each guide its own prerequisites, complete files or clearly labeled
excerpts, commands, and expected results. Give [Examples](EXAMPLES.md) complete
application setups. Do not assume a reader ran an unrelated earlier example.

Use a table of contents near the top of major documents and sentence-case
headings. Use `<details>` for long examples. GitHub callouts have specific uses:

| Marker | Use |
| --- | --- |
| `[!TIP]` | Optional workflow advice. |
| `[!NOTE]` | Helpful background. |
| `[!IMPORTANT]` | Required prerequisite or architecture rule. |
| `[!WARNING]` | Deprecated behavior, temporary bugs, or costly operations. |
| `[!CAUTION]` | Destructive or security-relevant actions. |

Place the marker alone on its blockquote line; GitHub ignores custom titles.

## Static figure rules

Static documentation figures live in [docs/assets](assets/). Graphigs owns
repeatable builders and the [figure visual tokens](References.md#figure-visual-tokens).
Change a figure's source and regenerate the output when a builder exists.
Small SVGs without a builder may be edited directly.

Keep the canvas transparent, black text on a readable fill, and neutral strokes
for outlines and edges. Use the existing Graphigs theme for colors and
fonts. Explain what distinct visual treatments mean; do not give actions and
components identical styling. Embed figures in a centered Markdown table with
a numbered caption. Keep theme swatches in Graphigs rather than duplicating them.

## Verification

Run the tools from the project environment:

```shell
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/python -m pytest
```

For documentation, execute changed examples in disposable directories and
check each result against the prose. Check file links and heading anchors,
including links back from reference tables. Read the introduction without prior
project knowledge: every component name must be defined before it is needed.
Run `git diff --check` and inspect the diff for unrelated changes.

Before finishing, review names, duplicated helpers, comments, and module
ownership. Add a TODO only for a real unresolved issue and check for an existing
entry first. Report verification and unresolved work with a copyable commit
message. Commit or publish only when requested.

## Releases

`CHANGELOG.md` is the source for GitHub Release notes. Before a release, move
every entry from `[Unreleased]` into a new `# [MAJOR.MINOR.PATCH] - YYYY-MM-DD`
section, add its table-of-contents link, and leave a complete empty
`[Unreleased]` section above it.

Before the first push, create and commit the generated dependency files:

```bash
just lock
git add uv.lock pylock.toml
git commit -m "Lock project dependencies"
```

The CI and release workflows use `uv sync --locked`, so they intentionally
fail when the committed lock no longer matches `pyproject.toml`.

Run the local rehearsal first:

```bash
just release-check
```

Run the release:

```bash
just release patch
```

> [!WARNING]
> `just release` creates the version commit and annotated tag, then atomically
> pushes `main` and the tag. It returns after the push without waiting for
> GitHub Actions.

GitHub Actions runs CI, validates wheel and sdist installs on Python 3.12 and
3.13, and creates the GitHub Release with the changelog section as its notes.
The workflow publishes the validated artifacts to PyPI when the tagged
`justfile` contains:

```just
RELEASE_PYPI := "true"
```

Keep the generated default at `"false"` for private packages and GitHub-only
releases. Configure PyPI trusted publishing for the `pypi` GitHub environment
before setting it to `"true"`.

> [!IMPORTANT]
> Edit and commit this setting before the release. Shell variables and
> `just --set` overrides are not stored in the tag and cannot select PyPI.

To stop after creating the checked local commit and tag, run the steps
separately:

```bash
just release-prepare patch
just release-push vMAJOR.MINOR.PATCH
```

> [!NOTE]
> If the GitHub Release exists but PyPI was skipped, run
> `just publish-pypi vMAJOR.MINOR.PATCH`. This requires an authenticated `gh`
> command. The recovery workflow downloads the existing release assets and
> never rebuilds them.
