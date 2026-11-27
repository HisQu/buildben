# Changelog

All notable changes to `{my_project}` will be documented in this file.

This changelog follows Keep a Changelog 2.0.0 and Semantic Versioning 2.0.0.

See the [changelog rules](CONTRIBUTING.md#changelog).

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

## [Unreleased]

<br>

### ✨ Added

- Added committed-project snapshot authoring and Linux/Windows native setups
  with `SHA256SUMS`; authored app hooks now ship in the installed package.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Generated projects no longer provide root install, launch, or
  uninstall helper scripts. Checkout registration now uses
  `uv run --locked <command> app install -e`; releases use the platform
  `<app-id>-setup-*` executable.
  Affected: Maintainers and users of generated helper scripts or the former
  source-selection installer.
  Migration: Synchronize the existing checkout with `uv sync --locked` and run
  `uv run --locked <command> app install -e`, or run the matching release setup.

<br>

### 🗑️ Deprecated

<br>

### 🔥 Removed

- Removed legacy receipt migration and replacement options from installer wrappers.

<br>

### 🐛 Fixed

<br>

### 🔒 Security

<br>

---

<br>

<!-- ======================================================== -->

## [{initial_version}] - {scaffold_date}

<br>

### ✨ Added

- Released `{my_project}`.
- Added src-layout packaging, Typer CLI entrypoints, AppRC configuration, documentation, tests, and maintainer tooling.
