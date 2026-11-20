# Buildben Changelog

All notable changes to `buildben` will be documented in this file.

This changelog follows Keep a Changelog 2.0.0 and Semantic Versioning 2.0.0.

> [!IMPORTANT]
> ## Rules
> 1. Follow [Keep a Changelog 2.0.0](https://keepachangelog.com/en/2.0.0/) and [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).
> 2. Keep the project’s complete release history in this file. Do not move older releases to an archive.
> 3. Use `## [VERSION] - YYYY-MM-DD [YANKED]` for released headings; include `[YANKED]` only for a yanked release. Keep empty categories under [Unreleased] and omit empty categories from released sections.
> 4. Include only curated changes with a notable effect on users or contributors. Exclude routine internal refactors, test-only work, and other changes without a user- or contributor-facing effect; resolving an issue alone does not require an entry.
> 5. File entries under their actual category. Start every breaking entry with **Breaking:** 💥 under that category, identify affected users, and include migration guidance when possible.
> 6. Use the emoji mapping informed by [Gitmoji](https://github.com/carloscuesta/gitmoji) and [conventional-changelog-emoji](https://github.com/favoloso/conventional-changelog-emoji): ✨ Added, 🛠️ Changed, 🗑️ Deprecated, 🔥 Removed, 🐛 Fixed, and 🔒 Security.
> 7. Describe each Beta (`bN`) and Pre-release (`rcN`) since the preceding release. Summarize each stable release since the preceding stable release and link to that comparison.
> 8. Use 🐛 Fixed only for defects in previously released behavior; describe new features under ✨ Added.
> 9. List [Unreleased] and major/minor `X.Y.0` releases in the TOC; omit patch and preview releases. Place version reference definitions immediately after the TOC. [Unreleased] compares the latest existing release tag with HEAD; tagged releases compare with the previous existing tag, or link to the release page when no previous tag exists. Use only existing tags.
>
> Local presentation exceptions: retain the project header, rules block, TOC, and `<br>` / `---` layout; use emoji-prefixed category headings and the inline 💥 breaking marker; keep all six category headings under [Unreleased] even when empty; list only [Unreleased] and `X.Y.0` releases in the TOC, leaving patch and preview releases in history but out of the TOC; place reference definitions immediately after the TOC instead of at the bottom.

<br>

### Table Of Contents

1. [Buildben Changelog](#buildben-changelog)
2. [\[Unreleased\]](#unreleased)
3. [\[0.13.0\] - 2026-11-11](#0130---2026-11-11)
4. [\[0.11.0\] - 2026-10-21](#0110---2026-10-21)
5. [\[0.10.0\] - 2026-10-21](#0100---2026-10-21)
6. [\[0.9.0\] - 2026-09-28](#090---2026-09-28)
7. [\[0.8.0\] - 2026-09-28](#080---2026-09-28)
8. [\[0.7.0\] - 2026-09-07](#070---2026-09-07)
9. [\[0.6.0\] - 2026-08-31](#060---2026-08-31)
10. [\[0.5.0\] - 2026-08-31](#050---2026-08-31)
11. [\[0.4.0\] - 2026-07-03](#040---2026-07-03)
12. [\[0.3.0\] - 2026-07-01](#030---2026-07-01)

<br>

---

<br>

[Unreleased]: https://github.com/HisQu/buildben/compare/v0.13.0...HEAD
[0.13.0]: https://github.com/HisQu/buildben/compare/v0.11.3...v0.13.0
[0.11.3]: https://github.com/HisQu/buildben/compare/v0.11.2...v0.11.3
[0.11.2]: https://github.com/HisQu/buildben/compare/v0.11.1...v0.11.2
[0.11.1]: https://github.com/HisQu/buildben/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/HisQu/buildben/compare/v0.10.3...v0.11.0
[0.10.3]: https://github.com/HisQu/buildben/compare/v0.10.2...v0.10.3
[0.10.2]: https://github.com/HisQu/buildben/compare/v0.10.1...v0.10.2
[0.10.1]: https://github.com/HisQu/buildben/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/HisQu/buildben/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/HisQu/buildben/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/HisQu/buildben/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/HisQu/buildben/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/HisQu/buildben/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/HisQu/buildben/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/HisQu/buildben/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/HisQu/buildben/releases/tag/v0.5.0

<!-- ======================================================== -->

## [Unreleased]

<br>

### ✨ Added

- Publish Beta and Pre-release builds from local artifacts, with three rolling
  downloads per channel and permanent changelog entries.

- Add opt-in `init-proj NAME --frontend react` scaffolding with project-local
  React, TypeScript, Vite, Bun lockfile, ESLint, and Vitest component testing.
  Generated roots expose grouped `just front sync|dev|check|test|build` recipes
  and an independent frontend CI job without changing Python-only generation
  or Python dependency and distribution ownership.

- Added complete-project native setup authoring and hybrid static-asset
  preparation. Generated AppRC apps share typed application hooks, recorded
  runtime dispatch and lightweight editable registration.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Replaced generated lifecycle wrappers/payloads and schema-2 uv-tool
  installation with complete locked project snapshots, schema-3 runtime slots
  and one stable native command. Existing installations need explicit
  resource-preserving retirement/reinstallation; generated apps and automation
  must use native setup or `uv run --locked <app> app install -e`. No converter,
  old source selector or wheel override compatibility layer remains.

- **Breaking:** 💥 `just make-artifacts` now compiles setup and requires the authoring
  Rust/LLVM/cargo-xwin toolchain. Only two setup executables and `SHA256SUMS`
  are final native outputs under ignored `dist/`; intermediate copies stay in
  ignored `.cache/apprc/`. Do not commit generated artifacts or expect separate
  launcher/uninstaller assets.

- CI now runs feature branches through pull requests and cancels superseded checks. Release hosted-CI gating is controlled separately by `RELEASE_REQUIRE_CI`; generated projects retain mandatory local tests.

- Pin authoring and generated projects to the immutable AppRC cutover source,
  while keeping Buildben's argparse business CLI and empty runtime dependency
  list. Normal pip installation remains independent of AppRC.

<br>

### 🗑️ Deprecated

<br>

### 🔥 Removed

<br>

### 🐛 Fixed

<br>

### 🔒 Security

<br>

---

<br>

<!-- ======================================================== -->

## [0.13.0] - 2026-11-11

<a id="0120---2026-10-29"></a>

Includes the changes previously prepared under unpublished 0.12.0 and Unreleased.
The previous published release was 0.11.3.

<br>

### ✨ Added

- Added `--main` to repository and generated-project installers. It captures one
  immutable GitHub main commit with matching source/runtime inputs; stable
  releases remain the default.

- Added authored AppRC lifecycle generation and standalone bootstraps that acquire
  uv/Python without requiring AppRC or the application first. Checkout installation
  uses the actual editable project, including dirty source changes. Private
  temporary-directory aliases are normalized without relaxing managed-resource
  containment or lifecycle link checks.

- Added first-install native/single-root choice, explicit persistent switching,
  and durable installation metadata separate from disposable state. Layout affects
  declared resources, not uv's program environment or dependencies; resource
  components remain independently optional.

- Added saved inspection/removal support outside the removable environment,
  actual-process exit handoff, current-format recovery and generation-safe
  authority retirement. Program-only removal preserves resource data/support;
  complete removal requires ownership-aware preview and consent. Shared uv/Python,
  editable checkouts and workspaces are not implicit targets.

- Added integrity-bound release staging and verification. Draft retries preserve
  tag ownership and partial-upload semantics; finalization validates the exact
  package/helper asset contract before publication.

- Added root `CONTRIBUTING.md`, audience-grouped documentation navigation, and
  generated-document link checks across README, contributor/agent guidance and
  detailed documentation.

- Added an isolated Actions artifact round-trip diagnostic to generated projects,
  with dedicated-branch bootstrap, manual dispatch and cleanup guidance.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Generated applications use AppRC's independent resource, durable
  installation and grouped maintenance contracts. Affected: consumers of the old
  storage/appdata commands, receipt installers, or schema-1 authority. Migration:
  update declarations and mounting, finish old operations with their original
  generation, preserve resources, retire old authority, and install fresh.
  Do not infer an old layout or rerun `init-proj` over an existing project.
  See the [upgrade guidance](README.md#uninstall).

- **Breaking:** 💥 Replaced `_dev/distribution` and platform-specific root installer
  copies with authored `<app>_distr` composition and six `app-install`,
  `app-launch` and `app-uninstall` `.sh`/`.cmd` wrappers. Affected: automation
  maintaining copied lifecycle code. Migration: preserve project actions in the
  ordinary-Python payload, regenerate through its `_distr.make_artifacts` module,
  and validate with `just check-artifacts`. Application wheels exclude the
  author-only `_distr` package; source archives include its required inputs.

- **Breaking:** 💥 GitHub releases require package/native-helper assets and an
  integrity-bound `release-manifest.json`, not just a wheel and sdist.
  Affected: release automation and consumers assuming a two-file release.
  Migration: stage and validate the exact repository/tag/commit asset set before
  uploading. PyPI publication remains disabled by the committed policy.

- **Breaking:** 💥 Generated projects declare matching immutable AppRC core/terminal
  requirements directly, including ordinary pip installs, rather than relying
  on uv-only overrides. Installer authors must regenerate canonical
  `management.py`/`management.json` support and remove old private filename
  assumptions. Existing projects are not rewritten automatically; public root
  launch/uninstall wrappers and Buildben's zero-runtime-dependency contract remain.

- **Breaking:** 💥 Scaffolds use root `BACKLOG.md` rather than `TODO.md` for deferred
  work. Update existing links and rename the durable backlog while preserving its
  entries. Reserve `TODO.md` for active-pass checklists beside `PLAN.md`; the
  scaffold generates neither active artifact. Do not rerun `init-proj` to migrate.

- New scaffolds preserve the existing README as the project's chosen design;
  agents need approval before substantial restructuring. Generated badges and
  table-of-contents links remain valid after project-name substitution.

- CONTRIBUTING owns shared rules and everyday checks; Development retains deeper
  guides, and agent instructions link to those rules rather than duplicate them.

- Archive checks validate normalized wheel/source filenames, including project
  names with underscores. Authoring/staging recipes use the locked interpreter
  without requiring an activated environment or direnv.

- Git preserves canonical generated command bytes with CRLF-aware whitespace
  checking, including the policy in new scaffolds.

- Maintained and scaffolded CI run on Linux/Python 3.12 and 3.13. Native
  Windows/macOS validation remains deferred; WSL agents must not launch native
  Windows verification executables. Explicitly authorized Linux-only integration
  does not establish Windows/macOS release readiness.

<br>

### 🔥 Removed

- **Breaking:** 💥 Removed receipt adoption/replacement and the `--migrate-legacy`,
  `--reinstall-legacy`, `--legacy-source`, and `--legacy-quiescent` options.
  Scripts using those options must use a fresh schema-2 installation instead;
  current resource/layout migration remains resumable.

<br>

### 🐛 Fixed

- Fixed the Unix Buildben installer calling a configuration command that Buildben
  does not provide. Generated applications retain their setup wizard.

<br>

---

<br>

<!-- ======================================================== -->

## [0.11.3] - 2026-10-22

<br>

### ✨ Added

- Public HTTPS installation is independent of GitHub CLI; authenticated users
  can select `--github-client gh`. READMEs link GitHub CLI installation/setup,
  and generated README templates keep both transports' commands as comments.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Upgrading from 0.10.3 or earlier replaces custom installation
  payloads with a wheel and locked source distribution; installer `--git` and
  `--dev` modes are removed. Affected: Users of those modes or payload assets.
  Migration: Use the README one-liner or an ordinary clone/venv/editable install.
  See [0.11.0](#0110---2026-10-21) for transport and source-lock details.

<br>

### 🐛 Fixed

- Preserve the release-notes output directory when building with a supplied
  notes file, as the draft-release workflow does.

- Support Windows PowerShell 5.1 source installation, including default and
  explicitly selected release versions.

<br>

---

<br>

<!-- ======================================================== -->

## [0.11.2] - 2026-10-22

<br>

### 🛠️ Changed

- **Breaking:** 💥 Upgrading from 0.10.3 or earlier replaces custom installation
  payloads with a wheel and locked source distribution; installer `--git` and
  `--dev` modes are removed. Affected: Users of those modes or payload assets.
  Migration: Use the README one-liner or an ordinary clone/venv/editable install.
  See [0.11.0](#0110---2026-10-21) for transport and source-lock details.

<br>

### 🐛 Fixed

- Preserve Python program quotes when the Windows installer runs under Windows
  PowerShell 5.1 by passing program text through stdin.

<br>

---

<br>

<!-- ======================================================== -->

## [0.11.1] - 2026-10-21

<br>

### 🐛 Fixed

- Run the source-install verification recipe in the locked uv project
  environment instead of the host Python, where `pytest` may be unavailable.

<br>

---

<br>

<!-- ======================================================== -->

## [0.11.0] - 2026-10-21

<br>

### ✨ Added

- Select authenticated GitHub access with `--github-client gh`; public downloads
  use anonymous HTTPS by default. READMEs link GitHub CLI installation and setup.

- Generated source distributions include `uv.lock` and `pylock.toml`; generated
  README templates retain public and authenticated commands as comments.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Installers now install published source distributions using their
  committed lock. Removed installer `--git` and `--dev` modes and the custom
  installation archives, manifest, helper and runtime-export assets.
  Affected: Installer-mode users and consumers of the former release payload.
  Migration: Use a documented one-line installer, or clone the repository and
  install with `python -m pip install -e .` in a virtual environment. Releases
  now publish only the standard wheel and source distribution.

<br>

### 🐛 Fixed

- Public installation no longer fails merely because an unauthenticated `gh`
  executable is installed.

<br>

---

<br>

<!-- ======================================================== -->

## [0.10.3] - 2026-10-21

<br>

### 🐛 Fixed

- Send an explicit `Content-Length` with binary release uploads so GitHub
  accepts them.

<br>

---

<br>

<!-- ======================================================== -->

## [0.10.2] - 2026-10-21

<br>

### 🐛 Fixed

- Resolve existing release drafts through authenticated paginated listings,
  avoiding the published-only tag lookup endpoint.

<br>

---

<br>

<!-- ======================================================== -->

## [0.10.1] - 2026-10-21

<br>

### 🐛 Fixed

- Disable setup-uv caching in release jobs that do not populate the cache,
  preventing cache-save failures.

<br>

---

<br>

<!-- ======================================================== -->

## [0.10.0] - 2026-10-21

<br>

### ✨ Added

- BuildBen's own `just` recipes are grouped by task with `[group('...')]` for
  easier browsing.

- Generated projects include optional `just worktree-create` and
  `just worktree-remove` recipes for isolated, locked development checkouts.

- Add thin platform archives containing installers, a manifest, and lock-derived
  runtime requirement and constraint exports. The application wheel and source
  archive remain separate release assets; the installer downloads the wheel.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Manual PyPI publication now requires `RELEASE_PYPI := "true"` in
  both the current committed `justfile` and the target tag's committed
  `justfile`. Affected: maintainers who used the manual command or workflow
  while either policy was false. Migration: commit `"true"` before preparing
  a release intended for PyPI, then use an active workflow ref and target tag
  that both contain that committed setting.

- **Breaking:** 💥 Ordinary installer use now resolves a published non-prerelease
  release and installs its validated thin payload instead of automatically
  selecting a Git checkout or local wheel. Affected: users of the default
  installer, especially while existing releases lack this payload. Migration:
  use explicit `--git` or `--dev [PATH]` until a future release publishes one.

- `just release-prepare` now performs fast version, lock/export, release-note,
  wheel/sdist, and Twine checks; `just release-check` remains the explicit full
  local rehearsal.

- Tag release workflows reuse successful normal CI for the exact commit and
  publish the draft only after build and platform installation checks pass.

<br>

### 🐛 Fixed

- Preserve canonical installer executable modes when staging platform archives.

- Use correctly escaped native file URIs for Windows artifact-install smokes,
  and export the configured repository for local release-input builds.

- Support macOS Bash 3.2 and preserve native Windows paths and CMD arguments
  when exercising the platform installer from Git Bash.

- Standard-library release and archive operations no longer synchronize the
  full development environment.

- Tag jobs reuse already prepared release notes when supplied, stage the full
  validated payload, and build one platform archive per matrix target.

- Build platform archives from the common downloaded assets, reconstructing
  canonical platform launchers and restoring Unix executable modes.

- Pass Windows asset-directory paths with forward slashes so native argument
  quoting preserves payload paths containing spaces.

<br>

---

<br>

<!-- ======================================================== -->

## [0.9.1] - 2026-10-02

<br>

### 🛠️ Changed

- Changed: Scaffolded installation docs now put the one-line install before the cloned-repository install, label platform commands, and explain how to remove the application and uv.

<br>

---

<br>

<!-- ======================================================== -->

## [0.9.0] - 2026-09-28

<br>

### ✨ Added

- Generated projects include online, Git checkout, and local wheelhouse
  installation modes. Their README documents the modes and keeps a placeholder
  for a future offline bundle.

<br>

---

<br>

<!-- ======================================================== -->

## [0.8.0] - 2026-09-28

<br>

### ✨ Added

- Mermaid flowchart and class diagram starters now come from Graphigs. Maintainers
  can refresh Buildben's scaffold snapshots or check them for drift.

- An Examples page with complete storage, environment override, shared user
  preferences, and multiple config-section setups.

- Documentation checks for generated links, anchors, page labels, and runnable
  examples against the installed AppRC package.

<br>

### 🛠️ Changed

- **Breaking:** 💥 New projects require `apprc>=0.25.0,<0.26` and use `AppRC`,
  `ResolvedConfig.build()`, and `rc.cli.mount_config_cli()`. Config imports now
  come from `config.app`, `config.bundle`, and section modules.
  Affected: Users adopting regenerated templates in an existing project.
  Migration: Replace `.storage_only()`, `.spec`, `.mount_cli()`, and
  `.env_bootstrap` with the generated examples. Import classes from their modules
  instead of the removed config catalog and lazy facades.

- **Breaking:** 💥 Generated projects use `apprc.defaults.env`, `apprc.storage.env`,
  and `<APP>_APPRC_DIR/apprc.toml` instead of the custom legacy filenames.
  Affected: Existing projects adopting the new config declaration.
  Migration: Preserve existing data directories; copy packaged defaults and
  storage overrides to the new filenames, set `<APP>_APPRC_DIR`, and register
  existing roots with `config storage add`. Keep legacy files until values and
  storage selection have been verified.

- Generated documentation now groups H2 sections under topical H1 headings.
  Generated projects test their table-of-contents order and major-section
  spacing during CI.

- Generated documentation explains components before dependent tasks and links
  explanations, guides, and references at the relevant words. Documentation and
  AGENTS.md require fixed terminology, independent examples, and concrete prose.

- The generated starter keeps storage-only behavior and standard-library logging.
  Buildben's runtime dependencies remain empty.

<br>

### 🐛 Fixed

- Generated entrypoints, utility imports, and release helpers pass the starter's
  Ruff checks without an initial cleanup pass.

- The release-note check accepts the root changelog's `Breaking changes`
  heading.

<br>

---

<br>

<!-- ======================================================== -->

## [0.7.1] - 2026-09-07

<br>

### 🐛 Fixed

- Install `just` in Buildben CI before tests that execute generated release
  recipes.

<br>

---

<br>

<!-- ======================================================== -->

## [0.7.0] - 2026-09-07

<br>

### ✨ Added

- Add `release-prepare` and `release-push` recipes for step-by-step releases.

- Add `publish-pypi TAG` and a manual GitHub Actions job that publishes the
  wheel and source archive attached to an existing GitHub Release.

<br>

### 🛠️ Changed

- **Breaking:** 💥 `just release` now prepares the release and atomically pushes
  `main` plus the new tag instead of stopping after local tag creation.
  Affected: Maintainers who use `just release` only to prepare local release
  state.
  Migration: Use `just release-prepare` for the previous local-only behavior,
  or use `release-prepare` followed by `release-push` for manual control.

- **Breaking:** 💥 Tag workflows now read the tracked `RELEASE_PYPI` setting from the
  tagged `justfile` instead of the `PUBLISH_PYPI` GitHub repository variable.
  Affected: Maintainers whose release workflow uses `PUBLISH_PYPI=true`.
  Migration: Set `RELEASE_PYPI := "true"` in the `justfile` for projects that
  publish every release to PyPI. The old repository variable can be removed.

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

## [0.6.0] - 2026-08-31

<br>

### 🛠️ Changed

- **Breaking:** 💥 Newly scaffolded projects replace
  `<my_project>.config.owners.AppRuntimeConfig` with
  `<my_project>.config.sections.app.AppSettings` and a project-named config
  bundle.
  Affected: Downstream code that imports generated configuration internals.
  Migration: Import `AppSettings` from `config.sections.app`, or import the
  generated bundle through the config facade. New projects should add settings
  below `config/sections/`.

- Quiet release builds by hiding setuptools backend logs while keeping the
  release checks visible. Align Buildben and generated-project release recipes
  with Haiu's full dependency checks, recovery messages, and release status.

<br>

---

<br>

<!-- ======================================================== -->

## [0.5.0] - 2026-08-31

<br>

### ✨ Added

- Add GitHub CI and tag-triggered release workflows for Buildben and generated
  projects. The release workflow checks the changelog, validates wheel and
  sdist installs, then attaches both artifacts to a GitHub Release.

- Add local `just release-check` and `just release` recipes plus release-note
  and installed-distribution checks that use the changelog as the release-note
  source.

- Generate an initial package test so a new project's active CI test job has
  collected coverage from its first commit.

<br>

### 🛠️ Changed

- Make GitHub Releases the required publishing path. PyPI publishing is an
  opt-in trusted-publishing job that runs only after the GitHub Release and
  only when `PUBLISH_PYPI=true`.

- Document the tag release procedure and optional PyPI configuration in the
  generated project development guide.

<br>

### 🐛 Fixed

- Exclude archived template code from Pyright so it checks maintained source
  and tests without requiring obsolete dependencies.

<br>

---

<br>

<!-- ======================================================== -->

## [0.4.0] - 2026-07-03

<br>

### 🛠️ Changed

- **Breaking:** 💥 Generated project scaffolds now target AppRC 0.19.0 and expose
  `<my_project>.config.APP_RC` instead of the old `APP_CONFIG` kit alias.
  Affected: Users copying or extending generated scaffold internals that import
  `APP_CONFIG`, `AppConfigKit`, `EnvConfig`, `env_field`, or AppRC internal
  runtime modules.
  Migration: Use `import apprc as rc`, `APP_RC`, `rc.Config`, `rc.field(...)`,
  and `APP_RC.mount_cli(...)`.

- Update generated project configuration and CLI templates to AppRC 0.19.0's
  standard public facade.

<br>

---

<br>

<!-- ======================================================== -->

## [0.3.0] - 2026-07-01

<br>

### ✨ Added

- Add `TODO.md` to generated project scaffolds as a tracked follow-up list.

- Add a root `TODO.md` parking lot for buildben maintenance follow-ups.

- Add generated-project changelog and TODO maintenance rules so scaffolded repos preserve headers, table-of-contents blocks, and release-note structure.

<br>

### 🛠️ Changed

- Rename the project changelog template source from `_.CHANGELOG.md` to `_CHANGELOG.md` while continuing to generate `CHANGELOG.md`.

- Reference `TODO.md` in generated project docs and agent guidance.

<br>

---

<br>

<!-- ======================================================== -->

## [0.2.1] - 2026-06-26

<br>

### ✨ Added

- Add a project-filled changelog template to generated project scaffolds.

- Add generated-project coverage for changelog creation, package builds, wheel template contents, experiment scaffolds, and uv-based environment snapshots.

<br>

### 🛠️ Changed

- **Breaking:** 💥 Generated project scaffolds now target AppRC 0.15.1 and use the typed `EnvConfig` API.

- **Breaking:** 💥 Python template files now use `.py.tmpl` names so static tooling can scan the repository without parsing placeholder imports.

- Update generated project configuration to AppRC 0.15.1, including typed runtime config declarations and concrete AppRC import paths.

- Modernize `env-snapshot` to use `uv build` and `uv export` instead of `python -m build`, `pip-compile`, and unfinished Docker behavior.

- Make experiment scaffolds minimal and runnable without NumPy, Pandas, or a legacy project `env` module.

- Generate a root `README.md` in project scaffolds so package builds do not emit missing README warnings.

- Refactor project scaffolding into focused helper functions.

<br>

### 🔥 Removed

- Remove the broken `init-database` implementation from the public command tree.

- Remove Docker snapshot advertising from current documentation until Docker snapshot support is implemented.

- **Breaking:** 💥 The unfinished `init-database` / `data` command is no longer exposed.

<br>

### 🐛 Fixed

- Fix package-data coverage so experiment templates, including `_REPORT.md` and `_paths.env`, ship in buildben wheels.

- Fix repo-wide Ruff and Pyright workflows by moving placeholder Python templates to `.py.tmpl` files and scoping Pyright to package/tests.

- Fix generated experiment placeholder substitution for dates and human-readable experiment names.

<br>
