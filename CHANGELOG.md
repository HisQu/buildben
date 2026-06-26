# Buildben Changelog

All notable changes to `buildben` will be documented in this file.

This project follows Semantic Versioning.

<br>

### Table Of Contents

1. [Buildben Changelog](#buildben-changelog)
2. [[Unreleased]](#unreleased)
3. [[0.2.1] - 2026-06-26](#021---2026-06-26)

<br>

---

<br>

<!-- ======================================================== -->

# [Unreleased]

<br>

### 💥 Breaking Change Summary

<br>

### ➕ Added

<br>

### 💔 Changed

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
