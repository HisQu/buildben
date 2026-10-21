# Development

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Examples](EXAMPLES.md)

- [Work in the project](#work-in-the-project)
  - [Maintainer environment](#maintainer-environment)
  - [Use Git worktrees](#use-git-worktrees)
  - [Repository routing](#repository-routing)
  - [Before editing](#before-editing)
- [Document the project](#document-the-project)
  - [Documentation authoring](#documentation-authoring)
  - [Static figure rules](#static-figure-rules)
- [Verify and release](#verify-and-release)
  - [Verification](#verification)
  - [Releases](#releases)

<br>

# Work in the project

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

## Use Git worktrees

The optional `worktree-create` recipe makes a separate checkout from a Git
branch, tag, or commit and installs its locked dependencies into that checkout's
`.venv`. Run `just lock`, then commit `uv.lock` and `pylock.toml` on the base
branch first. This workflow needs `uv`, while the normal project install paths
above do not.

Run the command from the project repository. The recipe adds the new checkout
without changing your shell's directory. The destination's parent directory
must exist, and the destination itself must be new. Relative destinations are
resolved from the project root:

```shell
just worktree-create feature/parser "../parser trial" main
cd "../parser trial"
```

The branch must be a valid local name that does not already exist. The recipe
validates the destination, resolves the selected base to a commit before
creating the worktree, then runs
`uv sync --locked --all-extras --all-groups` inside it. The sync command sets
`UV_PROJECT_ENVIRONMENT` to the new worktree's `.venv`, regardless of an
inherited value. If dependency setup fails, the recipe keeps the worktree and
prints its path so you can inspect it.

Run removal from another worktree, such as the main checkout, after the
selected branch has been merged into local `main` and the checkout is clean:

```shell
just worktree-remove "../parser trial"
```

The recipe refuses the current or main worktree, worktrees nested inside each
other, a dirty worktree, a detached branch, or a branch that is not merged into
local `main`. By default it keeps the associated branch. To delete only that
merged branch, pass `true`:

```shell
just worktree-remove "../parser trial" true
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
| Mermaid starters | `assets/flowchart.IGNORE.mmd` and `assets/classdiagram.IGNORE.mmd` |

Buildben ignores the starter diagrams because their filenames contain
`.IGNORE.mmd`. Rename a diagram when you are ready to track and edit it.

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

<br>

# Document the project

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

The six `docs/` pages use topical H1 sections with H2 entries nested beneath
them in the table of contents. Put a standalone `<br>` before each topical H1.
The generated documentation test checks the hierarchy and spacing during
`pytest`. Use sentence-case headings and `<details>` for long examples. GitHub
callouts have specific uses:

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

<br>

# Verify and release

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

`just release-check` is the explicit full local rehearsal. The normal
`release-prepare` path performs fast release validation, updates the locked
version/export files, builds the wheel and sdist, and validates them; it does
not run the full rehearsal or browser suite.

```bash
just release-check
```

Run normal release preparation and push:

```bash
just release patch
```

> [!WARNING]
> `just release` creates the version commit and annotated tag, then atomically
> pushes `main` and the tag. It returns after the push without waiting for
> GitHub Actions.

The tag workflow reuses one successful full `ci.yml` run for the exact tagged
commit rather than repeating the full source matrix. It builds and validates
one wheel and source archive, then publishes only those two assets with release
notes in the GitHub release body. Normal CI exercises the source installer on
all six native OS/Python cells; the release job performs one Python 3.12 wheel
installation smoke and does not build platform installers.

`just build-release-inputs` accepts an optional positional path to already
validated release notes:

```shell
just build-release-inputs release/prepared-notes.md
```

Keep the supplied file outside `dist`, which the recipe rebuilds. Omit the
argument to generate notes from the changelog. Tag and version validation runs
in either case.

PyPI publication remains independently controlled by the tagged `justfile`
setting:
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

Manual publication and retries require `RELEASE_PYPI := "true"` in both the
current committed `justfile` and the target tag's committed `justfile`. The
manual workflow applies that check to its selected workflow ref and target
tag. If both policies are true and a GitHub Release already exists, publish
its attached artifacts without rebuilding them:

```bash
just publish-pypi vMAJOR.MINOR.PATCH
```

The command checks policy before GitHub authentication or network calls. A
false policy exits locally, and the manual workflow skips before requesting
the PyPI environment or OIDC token. When both policies are true, the
unprivileged preflight validates the Release assets, records their hashes and
release/tag/commit identities in a manifest, and uploads that exact snapshot.
The PyPI job publishes only the snapshot identified by the preflight artifact
ID.

The preflight detects a tag update or deletion during asset capture. Preventing
an administrator from changing or deleting the tag while preflight is running
requires repository tag protection or rulesets. This code does not configure
or verify those settings.
