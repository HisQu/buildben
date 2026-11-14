# Development

[Documentation](README.md) · [Explanations](Explanations.md) · [How-to user guides](How-To-User-Guides.md) · [References](References.md) · [Examples](EXAMPLES.md)

Read [Contributing](../CONTRIBUTING.md) for shared expectations, the normal setup
and checks, and submission guidance. This page explains the deeper procedures.

- [Work in the project](#work-in-the-project)
  - [Maintainer environment](#maintainer-environment)
  - [Use Git worktrees](#use-git-worktrees)
  - [Repository routing](#repository-routing)
- [Document the project](#document-the-project)
  - [Documentation authoring](#documentation-authoring)
  - [Static figure rules](#static-figure-rules)
- [Verify and release](#verify-and-release)
  - [Verification](#verification)
  - [Actions artifact diagnostic](#actions-artifact-diagnostic)
- [Native application authoring](#native-application-authoring)
  - [Windows installer verification procedure](#windows-installer-verification-procedure)
  - [Unix installer staging verification](#unix-installer-staging-verification)
  - [Releases](#releases)

---

<br>

# Work in the project

## Maintainer environment

Follow the [normal development setup](../CONTRIBUTING.md#set-up-development)
for a pip-based editable install. For a locked uv environment, use `just sync`
after [creating and committing the lock files](#releases). On Windows, Python
executables live under `.venv\Scripts`; on POSIX they live under `.venv/bin`.
The [dependency reference](References.md#dependency-declarations) distinguishes
runtime requirements from maintainer tools. uv, direnv, and just are optional
for the normal contributor install.

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
branch first. This workflow needs uv, while the
[normal contributor setup](../CONTRIBUTING.md#set-up-development) does not.

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

---

<br>

# Document the project

## Documentation authoring

1. Select the owning page using [Choose a document](README.md#choose-a-document),
   then inspect the relevant source and existing examples.
2. Follow the [documentation rules](README.md#documentation-rules) and
   [component names](README.md#component-names). Edit behavior, prose, and affected
   incoming and outgoing links together.
3. Run changed examples in an isolated directory and compare the results with
   the documented expectations. Keep each example independently usable.
4. Preview the affected pages and run the [documentation checks](#verification).
   Link checks catch missing targets, not unclear explanations or misleading claims.

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

---

<br>

# Verify and release

## Verification

Use the [normal checks](../CONTRIBUTING.md#run-checks), selecting the tests that
exercise changed behavior and running the project's required checks before
submission. Do not treat an unrelated passing test as evidence for an unexercised
path.

For documentation, run the generated project's maintained checks:

```shell
.venv/bin/python -m pytest tests/test_documentation.py
```

These check ordinary local Markdown links in the README, CONTRIBUTING, AGENTS,
and docs pages. They verify local files and heading anchors, not remote URLs,
GitHub's exact rendering, prose accuracy, or whether navigation is useful.

Execute changed examples in disposable directories and compare their output
and file changes with the prose. Preview the affected documents as well: the
checks cannot judge whether an explanation is understandable or a navigation
entry is useful. Read introductions without assuming prior project knowledge.

Report the commands and observed results, including failures, missing
prerequisites, and omitted checks. Keep the corresponding behavior unverified
until the relevant scenario has actually run.

## Actions artifact diagnostic

The [Diagnostics workflow](../.github/workflows/diagnostics.yml) checks Actions
artifact storage independently of normal CI and application/native checks.
It creates a tiny text file, uploads it, downloads that exact artifact by ID,
and compares the bytes. It needs no checkout, Python installation, configured
secrets, or repository-write permission.

For the initial proof before the workflow exists on default `main`, push
`.github/workflows/diagnostics.yml` on the exact branch
`diagnostics/artifact-upload`. Only a push to that branch changing that workflow
path triggers the diagnostic. After the workflow exists on default `main`, use
an authenticated GitHub CLI from the project repository for normal manual runs:

```shell
gh workflow run diagnostics.yml --ref <branch>
```

Replace `<branch>` with a branch containing the workflow. Each attempt retains
one artifact named `diagnostic-<run_id>-<run_attempt>` with a one-day retention
fallback; the workflow does not delete it immediately. After inspecting the
run, obtain its artifact ID from the upload step and delete only that artifact
using credentials with Actions artifact deletion permission:

```shell
gh api --method DELETE repos/OWNER/REPO/actions/artifacts/ARTIFACT_ID
```

Replace `OWNER`, `REPO`, and `ARTIFACT_ID` with the repository and that run's
artifact ID. A successful run proves only that this Actions artifact round-trip
worked at that time. It does not prove GitHub Release uploads, PyPI publication,
application correctness, all quota types, or future quota availability.

## Native application authoring

The application declaration and typed `InstallationHooks` live in the installed
package under `src/{my_project}/`. The separate
`src/{my_project}_distr/actions.py` contains distribution build actions; it is
not imported as an installed application hook.

`just make-artifacts` exports the committed Git revision (default `HEAD`) with its
complete workspace and unchanged `uv.lock`, builds React assets only in that
private copy, then asks AppRC to compile the Linux and Windows setup files.
For React projects, `just build-python-packages` uses the same verified private
source preparation and builds only the selected workspace package's wheel and
sdist. Python-only projects use plain `uv build` without the SDK authoring group
or lockfile. Neither route writes generated frontend files into the checkout.

Both authoring commands require Bun only for React projects; the ordinary Python
package command does not require AppRC's native compiler. No Bun, Git checkout,
or frontend source is required to use a built wheel. Native outputs stay under
`dist/` as setup files and `SHA256SUMS`; ordinary Python packages stay under
`.cache/apprc/python-packages/`. `just check-artifacts` validates native hashes
without rebuilding or writing.

## Windows installer verification procedure

> [!IMPORTANT]
> From WSL, never launch native Windows verification executables, directly or
> through helpers. This includes `powershell.exe`, `pwsh.exe`, Windows
> Python/pytest, `cmd.exe`, and Windows `uv`. Do not work around this boundary
> with a Windows virtual environment, subprocess wrapper, or alternate launcher.
> Use independent native Windows CI for Windows execution.


The generated CI workflow runs Linux checks only. Release staging cross-compiles
the Windows x64 setup but never executes that PE file. Cross-compilation and
Linux tests do not establish Windows runtime behavior; complete a separate
native Windows canary before relying on that setup.

Keep the boundary strict: from WSL, never launch native Windows executables,
PowerShell, CMD, Windows Python/pytest, or Windows `uv`, directly or through a
helper. If native Windows validation is unavailable, report it as pending rather
than changing runner policy or using Wine.

## Unix installer staging verification

The generated project's maintained tests exercise its AppRC declaration,
editable command contract, native setup outputs, and installed static package
data when React is enabled. They do not execute a Windows setup from WSL.

The release canary must exercise the actual Linux setup executable. Windows
cross-compilation and Linux tests do not establish Windows runtime behavior or
macOS filesystem behavior; use a separately authorized native runner.

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

The tag workflow builds the Python wheel/sdist through the private locked-source
preparation, then uses AppRC to produce the two native setup files and
`SHA256SUMS`. Only native files are uploaded as GitHub Release assets;
wheel/sdist publication remains governed separately by `RELEASE_PYPI`.

Native authoring runs with the pinned Rust and cross-compilation toolchain.
Windows setup output is not executed on Linux. No generated Python installer,
launcher executable, payload ZIP, or outer release manifest is published.

`just make-artifacts` builds native outputs from a selected committed source
revision; React projects use `just build-python-packages` to prepare assets
privately and build only the selected package, without native compilation.
Python-only projects use plain `uv build`, without requiring an SDK lockfile.
Both routes stage packages under `.cache/apprc/python-packages/`; native outputs
remain under `dist/`.
`just check-artifacts` reads declarations and validates native checksums without
compiling or rewriting. Linux behavior does not establish Windows runtime
behavior.

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
tag. If both policies are true and a GitHub Release already exists, the
workflow validates separately built wheel/sdist inputs against the selected
tag version and publishes only those two Python packages to PyPI. Native setup
files remain GitHub Release assets and never enter PyPI publication.

The preflight detects a tag update or deletion during asset capture. Preventing
an administrator from changing or deleting the tag while preflight is running
requires repository tag protection or rulesets. This code does not configure
or verify those settings.
