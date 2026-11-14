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
- Breaking: Generated projects no longer provide root install, launch, or
  uninstall helper scripts. Checkout registration now uses
  `uv run --locked <command> app install -e`; releases use the platform
  `<app-id>-setup-*` executable.
  Affected: Maintainers and users of generated helper scripts or the former
  source-selection installer.
  Migration: Synchronize the existing checkout with `uv sync --locked` and run
  `uv run --locked <command> app install -e`, or run the matching release setup.

### ➕ Added
- Added committed-project snapshot authoring and Linux/Windows native setups
  with `SHA256SUMS`; authored app hooks now ship in the installed package.

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
