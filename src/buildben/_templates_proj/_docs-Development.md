<!-- ======================================================== -->
## Table Of Contents
<!-- ======================================================== -->

1. [Development](#1-development)
2. [Maintainer Workflow](#2-maintainer-workflow)
   1. [Maintainer Loop](#maintainer-loop)
   2. [Repository Routing](#repository-routing)
   3. [Before Editing](#before-editing)
3. [Implementation Standards](#3-implementation-standards)
   1. [Source Editing Rules](#source-editing-rules)
   2. [Documentation Authoring](#documentation-authoring)
4. [Verification And Commit](#4-verification-and-commit)
   1. [Verification](#verification)
   2. [Review Checklist](#review-checklist)
   3. [Commit Checklist](#commit-checklist)

<br>

# 1. Development

Use this file before changing `{my_project}`.

<br>

# 2. Maintainer Workflow

<!-- ======================================================== -->
## Maintainer Loop
<!-- ======================================================== -->

The maintainer loop is:

1. Read [AGENTS.md](../AGENTS.md), this file, and the relevant docs chapter.
2. Check the current worktree.
3. Locate the source owner for the behavior.
4. Edit the smallest source surface that owns the behavior.
5. Run focused verification.
6. Run broader verification when shared behavior changes.
7. Review the Git diff.
8. Commit.

> [!NOTE]
> Related links:
> - Use [How-To User Guides](How-To-User-Guides.md) for user-facing command recipes.
> - Use [References](References.md) for exact paths, commands, and public surfaces.
> - Use [Explanations](Explanations.md) for the project model behind the workflow.

<br>

<!-- ======================================================== -->
## Repository Routing
<!-- ======================================================== -->

Put changes where the repo already has an owner.

| Change Type | Owner |
|---|---|
| Runtime package behavior | [src/{my_project}](../src/{my_project}) |
| Tests | [tests](../tests) |
| Small user-facing examples | [examples](../examples) |
| Static assets | [assets](../assets) |
| Documentation | [docs](.) |
| Project metadata and dependency declarations | [pyproject.toml](../pyproject.toml) |
| Development recipes | [justfile](../justfile) |
| Local agent guidance | [AGENTS.md](../AGENTS.md) |

Ask before creating a new top-level directory when one of these owners is a
reasonable fit.

> [!NOTE]
> Related: use [project paths](References.md#project-paths) for source file
> owners and [package layout](Explanations.md#package-layout) for import
> boundaries.

<br>

<!-- ======================================================== -->
## Before Editing
<!-- ======================================================== -->

Run these checks before a non-trivial change:

```bash
git status --short
rg --files
```

Then read the source owner and nearby files. For example, a CLI change usually
requires checking `src/{my_project}/cli/app.py`, the thin wrapper in
`src/{my_project}/main.py`, tests, README, and docs references.

> [!IMPORTANT]
> Do not weaken production contracts to make a test easier. Add or reuse a
> dedicated test helper when a test needs lighter setup.

> [!NOTE]
> Related: use [verification](#verification) for the local verification
> checklist.

<br>

# 3. Implementation Standards

<!-- ======================================================== -->
## Source Editing Rules
<!-- ======================================================== -->

Follow these rules for normal edits:

- Keep runtime behavior in [src/{my_project}](../src/{my_project}).
- Keep CLI behavior in `src/{my_project}/cli/app.py`; keep
  `src/{my_project}/main.py` wrapper-only.
- Keep tests in [tests](../tests).
- Reuse existing helpers before adding new helpers.
- Keep `__init__.py` files limited to imports and module docstrings.
- Prefer exact domain attributes over defensive probes against strict objects.
- Document public behavior with Sphinx-style docstrings.
- Update docs when a change affects setup, usage, CLI behavior, public APIs,
  environment variables, or user-visible workflows.

> [!NOTE]
> Related: use [public interfaces](References.md#public-interfaces) for the
> surfaces that need stable names and documentation.

<br>

<!-- ======================================================== -->
## Documentation Authoring
<!-- ======================================================== -->

Docs live in [docs](.) and follow the standards in [docs/README.md](README.md).

When editing docs:

1. Keep [docs/README.md](README.md) as the docs rules and reading map.
2. Put procedures in [How-To User Guides](How-To-User-Guides.md).
3. Put maintainer workflow in [Development](Development.md).
4. Put exact names in [References](References.md).
5. Put system concepts in [Explanations](Explanations.md).
6. Use separator comments before major sections.
7. Add direct links to source files when a reader may need to edit them.
8. Add `[!NOTE]` related-link callouts from concept sections to task recipes.
9. Use [figure visual tokens](References.md#figure-visual-tokens) when editing
   or adding docs figures.
10. Update figure assets when prose changes a diagrammed concept.

> [!NOTE]
> Related links:
> - Use [Markdown formatting rules](README.md#markdown-formatting-rules) for docs layout.
> - Use [link and backlink rules](README.md#link-and-backlink-rules) for related-link callouts.
> - Use [static figure rules](README.md#static-figure-rules) for docs assets.
> - Use [figure visual tokens](References.md#figure-visual-tokens) for docs figure colors.

<br>

# 4. Verification And Commit

<!-- ======================================================== -->
## Verification
<!-- ======================================================== -->

Run verification that matches the change.

For Python changes:

```bash
ruff format .
ruff check .
pyright
python -m pytest
```

For docs-only changes:

```bash
git diff --check
rg -n "TO[D]O|FIX[M]E|content[R]eference|oai[c]ite" README.IGNORE.md docs
python -c "import pathlib, xml.etree.ElementTree as ET; [ET.parse(p) for p in pathlib.Path('docs/assets').glob('*.svg')]"
```

> [!NOTE]
> The exact command depends on the local environment. If a command is not
> installed, state that in the final report and verify the closest safe
> surface.

<br>

<!-- ======================================================== -->
## Review Checklist
<!-- ======================================================== -->

Before finishing, review:

- The change is in the existing owner file or directory.
- New names match existing terminology.
- Docs link to exact files and exact chapters.
- Tests cover the behavior changed.
- The diff does not include unrelated formatting churn.
- New comments follow the local comment style.

> [!NOTE]
> Related: use [Development: before editing](#before-editing) before widening
> the scope of a change.

<br>

<!-- ======================================================== -->
## Commit Checklist
<!-- ======================================================== -->

Before committing:

1. Run focused tests for the touched area.
2. Run broader checks when shared behavior changed.
3. Review `git diff --check`.
4. Review `git status --short`.
5. Write a commit message that names the user-facing behavior.

> [!NOTE]
> Related: use [How-To User Guides: run tests](How-To-User-Guides.md#run-tests)
> for the short command recipe.
