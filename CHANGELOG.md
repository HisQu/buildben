# Buildben Changelog

All notable changes to `buildben` will be documented in this file.

This project follows Semantic Versioning.

> [!IMPORTANT]
> ## Rules
> 1. Keep this header and table of contents intact.
> 2. Before a release, move every entry from `[Unreleased]` into the new
>    version section and add that section to the table of contents.
> 3. Leave one empty `[Unreleased]` section with every release category after
>    preparing the version section. `just release` rejects a non-empty one.
> 4. Keep emojis, `<br>`, and `---` layout markers.
> 5. Describe the final difference from the previous release, not intermediate
>    refactors or fixes that no longer exist in the release.
> 6. Use `🔨 Fixed` only for defects in previously released behavior.

<br>

### Table Of Contents

1. [Buildben Changelog](#buildben-changelog)
2. [\[Unreleased\]](#unreleased)
3. [\[0.5.0\] - 2026-08-31](#050---2026-08-31)
4. [\[0.4.0\] - 2026-07-03](#040---2026-07-03)
5. [\[0.3.0\] - 2026-07-01](#030---2026-07-01)
6. [\[0.2.1\] - 2026-06-26](#021---2026-06-26)

<br>

---

<br>

<!-- ======================================================== -->

# [Unreleased]

<br>

### 💥 Breaking Change Summary

- Breaking: Newly scaffolded projects replace
  `<my_project>.config.owners.AppRuntimeConfig` with
  `<my_project>.config.sections.app.AppSettings` and a project-named config
  bundle.
  Affected: Downstream code that imports generated configuration internals.
  Migration: Import `AppSettings` from `config.sections.app`, or import the
  generated bundle through the config facade. New projects should add settings
  below `config/sections/`.

<br>

### ➕ Added

<br>

### 💔 Changed

- Quiet release builds by hiding setuptools backend logs while keeping the
  release checks visible. Align Buildben and generated-project release recipes
  with Haiu's full dependency checks, recovery messages, and release status.

<br>

### ⚠️ Deprecated

<br>

### 🗑️ Removed

<br>

### 🔨 Fixed

<br>

---

<br>

<!-- ======================================================== -->

# [0.5.0] - 2026-08-31

<br>

### ➕ Added

- Add GitHub CI and tag-triggered release workflows for Buildben and generated
  projects. The release workflow checks the changelog, validates wheel and
  sdist installs, then attaches both artifacts to a GitHub Release.
- Add local `just release-check` and `just release` recipes plus release-note
  and installed-distribution checks that use the changelog as the release-note
  source.
- Generate an initial package test so a new project's active CI test job has
  collected coverage from its first commit.

<br>

### 💔 Changed

- Make GitHub Releases the required publishing path. PyPI publishing is an
  opt-in trusted-publishing job that runs only after the GitHub Release and
  only when `PUBLISH_PYPI=true`.
- Document the tag release procedure and optional PyPI configuration in the
  generated project development guide.

<br>

### 🔨 Fixed

- Exclude archived template code from Pyright so it checks maintained source
  and tests without requiring obsolete dependencies.

<br>

---

<br>

<!-- ======================================================== -->

# [0.4.0] - 2026-07-03

<br>

### 💥 Breaking Change Summary

- Breaking: Generated project scaffolds now target AppRC 0.19.0 and expose
  `<my_project>.config.APP_RC` instead of the old `APP_CONFIG` kit alias.
  Affected: Users copying or extending generated scaffold internals that import
  `APP_CONFIG`, `AppConfigKit`, `EnvConfig`, `env_field`, or AppRC internal
  runtime modules.
  Migration: Use `import apprc as rc`, `APP_RC`, `rc.Config`, `rc.field(...)`,
  and `APP_RC.mount_cli(...)`.

<br>

### 💔 Changed

- Update generated project configuration and CLI templates to AppRC 0.19.0's
  standard public facade.

<br>

---

<br>

<!-- ======================================================== -->

# [0.3.0] - 2026-07-01

<br>

### ➕ Added

- Add `TODO.md` to generated project scaffolds as a tracked follow-up list.
- Add a root `TODO.md` parking lot for buildben maintenance follow-ups.
- Add generated-project changelog and TODO maintenance rules so scaffolded repos preserve headers, table-of-contents blocks, and release-note structure.

<br>

### 💔 Changed

- Rename the project changelog template source from `_.CHANGELOG.md` to `_CHANGELOG.md` while continuing to generate `CHANGELOG.md`.
- Reference `TODO.md` in generated project docs and agent guidance.

<br>

---

<br>

<!-- ======================================================== -->

# [0.2.1] - 2026-06-26

<br>

### 💥 Breaking Change Summary

- Generated project scaffolds now target AppRC 0.15.1 and use the typed `EnvConfig` API.
- The unfinished `init-database` / `data` command is no longer exposed.
- Python template files now use `.py.tmpl` names so static tooling can scan the repository without parsing placeholder imports.

<br>

### ➕ Added

- Add a project-filled changelog template to generated project scaffolds.
- Add generated-project coverage for changelog creation, package builds, wheel template contents, experiment scaffolds, and uv-based environment snapshots.

<br>

### 💔 Changed

- Update generated project configuration to AppRC 0.15.1, including typed runtime config declarations and concrete AppRC import paths.
- Modernize `env-snapshot` to use `uv build` and `uv export` instead of `python -m build`, `pip-compile`, and unfinished Docker behavior.
- Make experiment scaffolds minimal and runnable without NumPy, Pandas, or a legacy project `env` module.
- Generate a root `README.md` in project scaffolds so package builds do not emit missing README warnings.
- Refactor project scaffolding into focused helper functions.

<br>

### ⚠️ Deprecated

<br>

### 🗑️ Removed

- Remove the broken `init-database` implementation from the public command tree.
- Remove Docker snapshot advertising from current documentation until Docker snapshot support is implemented.

<br>

### 🔨 Fixed

- Fix package-data coverage so experiment templates, including `_REPORT.md` and `_paths.env`, ship in buildben wheels.
- Fix repo-wide Ruff and Pyright workflows by moving placeholder Python templates to `.py.tmpl` files and scoping Pyright to package/tests.
- Fix generated experiment placeholder substitution for dates and human-readable experiment names.
