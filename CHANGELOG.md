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
3. [\[0.7.1\] - 2026-09-07](#071---2026-09-07)
4. [\[0.7.0\] - 2026-09-07](#070---2026-09-07)
5. [\[0.6.0\] - 2026-08-31](#060---2026-08-31)
6. [\[0.5.0\] - 2026-08-31](#050---2026-08-31)
7. [\[0.4.0\] - 2026-07-03](#040---2026-07-03)
8. [\[0.3.0\] - 2026-07-01](#030---2026-07-01)
9. [\[0.2.1\] - 2026-06-26](#021---2026-06-26)

<br>

---

<br>

<!-- ======================================================== -->

# [Unreleased]

<br>

### 💥 Breaking changes

- Breaking: New projects require `apprc>=0.25.0,<0.26` and use `AppRC`,
  `ResolvedConfig.build()`, and `rc.cli.mount_config_cli()`. Config imports now
  come from `config.app`, `config.bundle`, and section modules.
  Affected: Users adopting regenerated templates in an existing project.
  Migration: Replace `.storage_only()`, `.spec`, `.mount_cli()`, and
  `.env_bootstrap` with the generated examples. Import classes from their modules
  instead of the removed config catalog and lazy facades.
- Breaking: Generated projects use `apprc.defaults.env`, `apprc.storage.env`,
  and `<APP>_APPRC_DIR/apprc.toml` instead of the custom legacy filenames.
  Affected: Existing projects adopting the new config declaration.
  Migration: Preserve existing data directories; copy packaged defaults and
  storage overrides to the new filenames, set `<APP>_APPRC_DIR`, and register
  existing roots with `config storage add`. Keep legacy files until values and
  storage selection have been verified.

<br>

### ➕ Added

- An Examples page with complete storage, environment override, shared user
  preferences, and multiple config-section setups.
- Documentation checks for generated links, anchors, page labels, and runnable
  examples against the installed AppRC package.

<br>

### 💔 Changed

- Generated documentation now groups H2 sections under topical H1 headings.
  Generated projects test their table-of-contents order and major-section
  spacing during CI.
- Generated documentation explains components before dependent tasks and links
  explanations, guides, and references at the relevant words. Documentation and
  AGENTS.md require fixed terminology, independent examples, and concrete prose.
- The generated starter keeps storage-only behavior and standard-library logging.
  Buildben's runtime dependencies remain empty.

<br>

### ⚠️ Deprecated

<br>

### 🗑️ Removed

<br>

### 🔨 Fixed

- Generated entrypoints, utility imports, and release helpers pass the starter's
  Ruff checks without an initial cleanup pass.

<br>

---

<br>

<!-- ======================================================== -->

# [0.7.1] - 2026-09-07

<br>

### 🔨 Fixed

- Install `just` in Buildben CI before tests that execute generated release
  recipes.

<br>

---

<br>

<!-- ======================================================== -->

# [0.7.0] - 2026-09-07

<br>

### 💥 Breaking Change Summary

- Breaking: `just release` now prepares the release and atomically pushes
  `main` plus the new tag instead of stopping after local tag creation.
  Affected: Maintainers who use `just release` only to prepare local release
  state.
  Migration: Use `just release-prepare` for the previous local-only behavior,
  or use `release-prepare` followed by `release-push` for manual control.
- Breaking: Tag workflows now read the tracked `RELEASE_PYPI` setting from the
  tagged `justfile` instead of the `PUBLISH_PYPI` GitHub repository variable.
  Affected: Maintainers whose release workflow uses `PUBLISH_PYPI=true`.
  Migration: Set `RELEASE_PYPI := "true"` in the `justfile` for projects that
  publish every release to PyPI. The old repository variable can be removed.

<br>

### ➕ Added

- Add `release-prepare` and `release-push` recipes for step-by-step releases.
- Add `publish-pypi TAG` and a manual GitHub Actions job that publishes the
  wheel and source archive attached to an existing GitHub Release.

<br>

### 💔 Changed

- Store the default PyPI release policy in version control and validate it
  before building release artifacts.
- Make PyPI publication retries check for identical existing files before
  uploading missing artifacts.
- Update release artifact upload and download actions in Buildben and generated
  projects.

<br>

---

<br>

<!-- ======================================================== -->

# [0.6.0] - 2026-08-31

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

### 💔 Changed

- Quiet release builds by hiding setuptools backend logs while keeping the
  release checks visible. Align Buildben and generated-project release recipes
  with Haiu's full dependency checks, recovery messages, and release status.

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
