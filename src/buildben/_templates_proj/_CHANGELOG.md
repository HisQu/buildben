# Changelog

All notable changes to `{my_project}` will be documented in this file.

This changelog follows Keep a Changelog 2.0.0 and Semantic Versioning 2.0.0.

> [!IMPORTANT]
> ## Rules
> 1. Follow [Keep a Changelog 2.0.0](https://keepachangelog.com/en/2.0.0/) and [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).
> 2. Keep stable sections and existing historical preview sections in this file. Git tags preserve each preview's changelog snapshot.
> 3. Use `## [X.Y.Z] - YYYY-MM-DD (b1)` or `## [X.Y.Z] - YYYY-MM-DD (rc1)` for a preview. Update the date and stage in the same heading as the target progresses. For stable, use `## [X.Y.Z] - YYYY-MM-DD`. Append `[YANKED]` only for a yanked release. Keep all six categories under [Unreleased] and omit empty categories from released sections.
> 4. Include only curated changes with a notable effect on users or contributors. Exclude routine internal refactors, test-only work, and other changes without a user- or contributor-facing effect; resolving an issue alone does not require an entry.
> 5. File entries under their actual category. Start every breaking entry with `**Breaking:** 💥` under that category, identify affected users, and include migration guidance when possible.
> 6. Use the emoji mapping informed by [Gitmoji](https://github.com/carloscuesta/gitmoji) and [conventional-changelog-emoji](https://github.com/favoloso/conventional-changelog-emoji): ✨ Added, 🛠️ Changed, 🗑️ Deprecated, 🔥 Removed, 🐛 Fixed, and 🔒 Security.
> 7. Keep one cumulative section per target version. Describe the changes that ship since the previous stable release, including earlier preview changes still present in the current build. Each GitHub Release gets a snapshot of that section.
> 8. Use 🐛 Fixed only for defects in previously released behavior; describe new features under ✨ Added.
> 9. List [Unreleased] and stable major/minor `X.Y.0` releases in the TOC. Place version reference definitions immediately after the TOC. [Unreleased] compares the latest existing release tag with HEAD. Link new stable entries to the previous stable comparison and use only existing tags.
>
> Local presentation exceptions: retain the project header, rules block, TOC, and `<br>` / `---` layout; use emoji-prefixed category headings and the inline 💥 breaking marker; keep all six category headings under [Unreleased] even when empty; list only [Unreleased] and `X.Y.0` releases in the TOC, leaving patch and preview releases in history but out of the TOC; place reference definitions immediately after the TOC instead of at the bottom.

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
