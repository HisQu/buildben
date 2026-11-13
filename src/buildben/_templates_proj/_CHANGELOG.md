# Changelog

All notable changes to `{my_project}` will be documented in this file.

> [!IMPORTANT]
> ## Rules
> 1) Do not remove or change this header and TOC without very good reason. 
> 1) When bumping version, move the sub-sections from `[Unreleased]` to
>    the new version -section. Remove empty sub-sections under released
>    versions. Provide a new `[Unreleased]` section at the top of the
>    changelog with all sections empty (don't remove those).
> 1) Do not remove emojis and use `<br>` and `---`.
> 1) Changelog entries must describe the final net difference from the
>    previous released version. Do not list intermediate pre-release
>    names, helper shapes, fixes, or refactors that were overwritten
>    before release.
> 1) Use `🔨 Fixed` only for defects in previously released behavior.
>    For new features, describe the final shipped behavior under `➕
>    Added`, even if the implementation went through pre-release fixes.



<br>

---

<br>

## Table Of Contents

1. [Changelog](#changelog)
   1. [Table Of Contents](#table-of-contents)
2. [\[Unreleased\]](#unreleased)
3. [\[{initial_version}\] - {scaffold_date}](#010---{scaffold_date})

<br>

---

<br>

<!-- ======================================================== -->

# [Unreleased]

<br>

### 💥 Breaking changes

<br>
- Breaking: Generated root `app-install.sh`, `app-install.cmd`,
  `app-launch.sh`, and `app-launch.cmd` entries are replaced by
  `app-install.py` and `app-launch.py` for checkout development; release
  installers are native platform executables.
  Affected: Maintainers and users invoking those root install/launch wrappers.
  Migration: Use the Python entries from a checkout and the matching
  `{my_project}-install-*` native executable from a release.

### ➕ Added
- Added SDK-authored Linux and Windows native release installers and launchers,
  with a retained authenticated runtime payload and exact outer asset manifest.

<br>

### 💔 Changed

<br>

### ⚠️ Deprecated

<br>

### 🗑️ Removed
- Removed legacy receipt migration and replacement options from installer wrappers.

<br>

### 🔨 Fixed

<br>

---

<br>

<!-- ======================================================== -->

# [{initial_version}] - {scaffold_date}

<br>

### ➕ Added

- Released `{my_project}`.
- Added src-layout packaging, Typer CLI entrypoints, AppRC configuration, documentation, tests, and maintainer tooling.
