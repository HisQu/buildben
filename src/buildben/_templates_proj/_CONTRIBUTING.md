# Contributing to `{my_project}`

These conventions apply to human contributors and coding agents. Start here for
the normal contribution workflow; use [Development](docs/Development.md) for
in-depth procedures and maintenance guides.

<br>

---

### Table of Contents

1. [Before starting](#before-starting)
2. [Quick start](#quick-start)
   1. [Set up development](#set-up-development)
   2. [Run checks](#run-checks)
3. [Working conventions](#working-conventions)
4. [Documentation and generated files](#documentation-and-generated-files)
   1. [README maintenance](#readme-maintenance)
   2. [Generated files](#generated-files)
5. [Before submitting](#before-submitting)

---

<br>

# Before starting

Check [existing issues](https://github.com/<github_username>/<my_project>/issues)
and [BACKLOG.md](BACKLOG.md) before starting overlapping work. Discuss substantial
behavior or design changes before implementing them. Read the relevant component
in [Explanations](docs/Explanations.md) and inspect nearby source and
`git status --short`. Keep unrelated changes untouched, and explain the intended
change before editing several files. Coding agents must also follow [AGENTS.md](AGENTS.md).

---

<br>

# Quick start

## Set up development

From the project root, use Python 3.12 or newer. Dependency groups require pip
25.1 or newer; upgrade pip inside the virtual environment before installing.

### For Linux & macOS

```shell
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e "." --group dev
```

### For Windows PowerShell

```powershell
py -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -e "." --group dev
```

This path does not require uv. The [maintainer environment](docs/Development.md#maintainer-environment)
guide covers uv, optional extras, and dependency declarations.

## Run checks

Run checks from the project root using the development environment.

### For Linux & macOS

```shell
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/python -m pytest
```

### For Windows PowerShell

```powershell
& '.\.venv\Scripts\ruff.exe' format --check .
& '.\.venv\Scripts\ruff.exe' check .
& '.\.venv\Scripts\pyright.exe'
& '.\.venv\Scripts\python.exe' -m pytest
```

Formatting checks do not modify files. Apply formatting fixes only to files you
edited; do not include unrelated formatting changes. The [verification guide](docs/Development.md#verification)
explains check selection and how to validate changed documentation and examples.

---

<br>

# Working conventions

- Keep each change focused. Follow the [repository layout](docs/Development.md#repository-routing)
  and ask before creating a top-level directory when an existing location fits.
- Check `{my_project}.config`, `{my_project}.utils`, `apprc`, and `apprc.cli`
  before adding helpers. Reuse existing implementations; place broadly reusable
  behavior in the appropriate shared module.
- App configuration belongs in `{my_project}.config.sections`. Keep fields in
  focused `rc.Config` classes with `rc.field(...)` declarations, assemble them
  in `config.bundle`, and declare the shared `APP_RC` in `config.app`. Import
  declarations and classes directly from their modules. Mount configuration
  commands with `rc.cli.mount_config_cli`; runtime values come from `state.resolved`.
- CLI behavior belongs in `{my_project}.cli.app`; keep `{my_project}.main` as a
  thin public entry point wrapper. Add minimal `__main__` demo code only when it
  improves discoverability or manual testing.
- Use stdlib `logging` for application-owned logs. Start AppRC integration with
  `import apprc as rc`.
- Import local utility helpers with `import {my_project}.utils as ut` and use
  explicit `ut.` prefixes. Keep package initializers limited to imports and
  module docstrings. For utility facades, use clean batch re-exports with
  file-level `# ruff: noqa: F401`, not redundant `symbol as symbol` aliases.
- Use exact attributes on known domain types. Model genuinely dynamic boundaries
  explicitly instead of probing strict objects defensively. Tests should use
  dedicated helpers rather than weaken production contracts to `Any`.
- Use Sphinx-style docstrings to specify public behavior. Avoid speculative
  abstractions and preserve public contracts unless the change explicitly
  includes their migration.

[BACKLOG.md](BACKLOG.md) holds durable actionable work not being handled now.
Keep an active pass's `TODO.md` execution checklist beside its `PLAN.md`; do not
create empty active artifacts or use TODO as a second backlog. Keep one
authoritative checklist per action, not duplicate editable checkboxes in a plan.
Before closing or archiving a pass, transfer unfinished work to the backlog or
another pass, checking for existing entries first.

---

<br>

# Documentation and generated files

Update documentation when a change affects setup, commands, public APIs,
environment variables, saved formats, or user-visible workflows. Record relevant
user-visible changes in [CHANGELOG.md](CHANGELOG.md); breaking changes must
identify affected users and explain migration when possible.

Follow the [documentation rules](docs/README.md#documentation-rules) and use the
[authoring guide](docs/Development.md#documentation-authoring) to carry them out.
Maintain affected incoming and outgoing links in the same change as their targets.

## README maintenance

The existing README is the project's chosen document design, not disposable
scaffold boilerplate. Adapt it in place; never replace it with a generic README
or regenerate it from scratch. Preserve CONTRIBUTING's established design too.

- Read the complete document before editing. Preserve section order, heading
  hierarchy and capitalization, HTML layout, badges, spacing elements, and useful
  existing content.
- Replace placeholders and starter descriptions with project-specific content.
  Correct stale facts, commands, and links within the existing design.
- Fit new information into existing sections unless they are unsuitable. Never
  remove useful content merely for brevity, style normalization, or your preferred
  format.
- Substantial restructuring requires a concrete project need and explicit user
  approval before editing. Explain what the current structure prevents and
  propose the smallest necessary change. Personal preference, generic best
  practices, and "cleaner formatting" are not sufficient reasons.
- Routine navigation maintenance is expected: add, remove, or update relevant
  entries and destinations when documents change. This is not a redesign and
  does not require redesign approval. Preserve the established audience groups,
  nesting, and presentation described in [README navigation](docs/README.md#readme-navigation).

## Generated files

When an asset has a source builder, edit that source and regenerate the output
rather than hand-editing generated files. Follow the [static figure guide](docs/Development.md#static-figure-rules)
for assets in `assets/` and `docs/assets/`, including Graphigs styling and captions.

---

<br>

# Before submitting

Review the diff for unrelated changes, duplicate helpers, naming drift, and
unnecessary abstractions. Run the relevant checks and report commands, observed
results, and any failed or omitted verification; do not imply unperformed checks
passed.

A pull request should explain the problem, intended behavior, verification, and
compatibility implications. Include affected documentation and changelog updates,
and migration instructions for breaking changes. Transfer real unfinished work
to the durable backlog instead of leaving misleading placeholders or claiming it
is complete. Coding agents must respect the user's commit and publication
permissions; a contribution guide does not grant release authorization.
