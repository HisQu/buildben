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

These validate the six `docs/` pages' grouped outlines and ordinary local
Markdown links in the README, CONTRIBUTING, AGENTS, and docs pages. They check
local files and heading anchors, not remote URLs or GitHub's exact rendering.

Execute changed examples in disposable directories and compare their output
and file changes with the prose. Preview the affected documents as well: the
checks cannot judge whether an explanation is understandable or a navigation
entry is useful. Read introductions without assuming prior project knowledge.

Report the commands and observed results, including failures, missing
prerequisites, and omitted checks. Keep the corresponding behavior unverified
until the relevant scenario has actually run.

## Windows installer verification procedure

> [!IMPORTANT]
> From WSL, never launch native Windows verification executables, directly or
> through helpers. This includes `powershell.exe`, `pwsh.exe`, Windows
> Python/pytest, `cmd.exe`, and Windows `uv`. Do not work around this boundary
> with a Windows virtual environment, subprocess wrapper, or alternate launcher.
> Use independent native Windows CI for Windows execution.

Use the existing [CI workflow](../.github/workflows/ci.yml) for the exact commit
under review. Its `installation` job has native `windows-latest` cells for
Python 3.12 and 3.13, running `just release-install-smoke`. Inspect the job logs
and report the commit, job, command, and observed result rather than treating a
workflow's presence as proof.

That recipe builds and extracts the project's sdist, installs it directly with
`uv tool install`, checks CLI help and the installed package snapshot, records
the installation, and exercises the saved native uninstaller while preserving
configuration and data sentinels. It does **not** execute `install-windows.ps1`
or the installer `.cmd` wrappers. A successful package-install smoke therefore
does not establish Windows installer-entrypoint correctness.

For an installer change, distinguish that existing package coverage from the
following native Windows evidence:

1. Exercise the actual
   [`src/{my_project}_dev/distribution/install-windows.ps1`](../src/{my_project}_dev/distribution/install-windows.ps1)
   file, not functions copied into a separate harness.
2. Exercise the documented downloaded `[scriptblock]::Create(...)` invocation
   from the [Windows one-line installation instructions](How-To-User-Guides.md#for-windows),
   with the downloaded content corresponding to the commit being verified.
   File invocation alone does not establish behavior in a downloaded script block.
3. Check that installer helpers share a mutable state object created locally
   for each invocation. Do not replace that shared object with copied scalar
   variables or `$script:` state: nested and downloaded script-block scopes
   must observe the same invocation-local updates without leaking state.

BuildBen's own native Windows regression tests exercise its canonical installer
and the project installer rendered through the real project scaffolder. That
central template coverage is separate from this generated project's CI package
smoke; this starter does not generate a `tests/test_release_install.py` suite or
a `-k windows_installer` test command. Do not claim generated installer proof
from the package smoke or a copied-function harness. Record any actual-file or
downloaded-entrypoint scenario that has not run as unverified.

Linux tests and static inspection are useful evidence only for the behavior
they exercise; they are not Windows execution proof. Capturing output,
`-NoProfile`, and `-NonInteractive` do not isolate a Windows console. Treat
`CREATE_NO_WINDOW` as an unverified workaround, not a verified cure for console
or control-event behavior.

If native Windows CI cannot run, report the blocker and keep Windows proof and
verification-dependent delivery pending. Do not launch Windows executables
from WSL to compensate, and do not change billing, runner policy, execution
policy, permissions, or other security settings to unblock verification.

## Unix installer staging verification

Unix staging changes need actual installer-entrypoint evidence, not only the
generated CI package-install smoke. BuildBen's maintained
[source-installer tests](https://github.com/HisQu/buildben/blob/main/tests/test_release_install.py)
render this Unix installer with matching project identity and run real source
installation and saved uninstallation with physical and symlinked temporary
parents. That central template coverage is separate from this project's
direct-package smoke.

Canonicalize only a newly created installer-owned staging root before deriving
extracted-source paths. Keep lifecycle and preflight link checks intact; do not
resolve arbitrary helper inputs, alter fixtures, or skip a failing smoke to hide
a production failure. Record missing project-specific installer evidence as
unverified rather than claiming it from another project's CI.

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
notes in the GitHub release body. Normal CI exercises direct sdist installation
on all six native OS/Python cells; the release job performs one Python 3.12 wheel
installation smoke and does not build platform installers.

The generated `just release-install-smoke` isolates HOME, AppRC/state, and uv
locations, validates the source archive version, and records its direct uv tool
installation with the stdlib lifecycle helper. It uses the saved native
uninstaller and verifies retained sentinels rather than deleting uv directly.
This direct-install route does not claim bootstrap ownership of its supplied uv.
Follow the [Windows installer verification procedure](#windows-installer-verification-procedure)
for the distinction between package-install coverage and installer-entrypoint
proof. Linux execution cannot establish CMD quoting, PowerShell preflight, or
executable-in-use behavior.

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
