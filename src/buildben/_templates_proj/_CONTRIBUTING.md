# Contributing to `{my_project}`

These conventions apply to human contributors and coding agents. Start here for
the normal contribution workflow; use [Development](docs/Development.md) for
in-depth procedures and maintenance guides.

<br>

---

### Table of Contents

1. [Before starting](#before-starting)
2. [Quick start](#quick-start)
3. [Working conventions](#working-conventions)
   1. [Issues and backlog](#issues-and-backlog)
   2. [Changelog](#changelog)
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

Follow the [development setup](docs/Development.md#set-up-development) for your
platform. Run the [project checks](docs/Development.md#run-checks) before
submitting a change.

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
  declarations and classes directly from their modules. Mount the shared
  `config` group and capability groups declared by `APP_RC` together through
  `rc.cli.mount_app_cli`; use `state.resolved` for runtime values. Keep
  `RuntimeIndependentCommand` for commands that must work without resolved
  runtime state, such as `appdata paths` and `appdata clean`:
  `runtime_independent_commands={"appdata": rc.cli.RuntimeIndependentCommand(action_prefixes={("paths",), ("clean",)}, skip_empty=True)}`.
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

## Issues and backlog

> [!CAUTION]
> These records can be published: Never record secrets, absolute paths, credentials, private host data, or speculative security claims. Use repository-relative source paths and full GitHub issue URLs. 


> [!IMPORTANT]
> 
> ## Rules
> 1) Preserve BACKLOG.md's header and TOC.
> 1) Order planned Passes and entries by intended execution. Use priorities, dependencies, shared work, checks, and effort to group entries. Keep Deferred last.
> 1) Do not suggest issues for paths that are under `## Ignore`
> 1) Create or update an issue for real, actionable, out-of-scope work. Add a concise linked backlog entry when selected. Reorder, batch, reconcile, or remove entries when useful.
> 1) Search open and closed issues and the backlog for the same work. Keep two-way links between related issues using their full URLs. Preserve relevant closed history.
> 1) For a complete fix, use a closing issue reference in the PR to main and remove the backlog entry in the same change. Use an ordinary reference for a partial fix and keep unresolved scope open. Add a CHANGELOG.md entry only when the change has a notable user- or contributor-facing effect.
> 1) **Types:**
>       - **Bug risk**: Potential defect with concrete evidence, not yet confirmed.
>       - **Code smell**: Implementation, architectural, maintainability or clarity issue that is not currently a defect.
>       - **Docs drift**: Documentation is stale, incomplete, or inconsistent.
>       - **Tooling**: Issue with build, test, lint, type-check, and general slowdown of developer workflow.
>       - **Security**: Evidence-backed security risk. Use Question for uncertainty.
>       - **Question**: Design, behavior, or ownership uncertainty needing investigation & maybe decision.
> 
> 1) **Priorities:**
>       - **P1**: Should be handled ASAP.
>       - **P2**: Should be handled before next release or milestone.
>       - **P3**: Useful cleanup for a later focused pass.
> 1) **Effort:**
>       - **E1**: Issue deserves its own focused pass.
>       - **E2**: Can be batched with a few other issues.
>       - **E3**: Can be batched with many other issues.
> 1) **Format:**
> ```markdown
> 
> <br>
> 
> # Pass: short name
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Issue:** https://github.com/OWNER/REPO/issues/NUMBER
> - **Area:**  `path/or/symbol`
> - **Observed while:** short context
> - **Why not fixed now:** scope, risk, uncertainty, or user decision needed
> - **Evidence:** concrete observation
> - **Context:** explanation to ensure the problem is understood in the big-picture of the repo.
> - **Suggested next step:** smallest reasonable follow-up. If applicable, reference related issues by URL.
> 
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Issue:** https://github.com/OWNER/REPO/issues/NUMBER
> - **Area:** `path/or/symbol`
> - ...
> 
> <br>
> 
> # Pass: another name
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Issue:** https://github.com/OWNER/REPO/issues/NUMBER
> - **Area:** `path/or/symbol`
> - ...
> ```

`accepted` marks focused work. `needs info` marks a concrete information gap
and is cleared when the missing information is supplied. `Deferred` marks work
deliberately retained for later. These labels are independent. BACKLOG.md sets
the schedule. Keep incoming reports out of the queue until selected.

If a Task is blocked, record the blocker on its issue and update the order as
needed. Independent Tasks within an authorized Pass may continue. A planned
Pass heading does not authorize starting it. Scheduling reopened issues
requires a fresh decision.

Keep one active checklist in `TODO.md` beside `PLAN.md`. Several checklist
steps may serve one issue. Before closing or archiving the checklist, transfer
durable follow-up to the appropriate issue and linked backlog entry when
selected. Carry any unfinished GitHub operation, its source evidence, and its
current outcome through the Pass's existing unfinished-work handoff. When
GitHub is unavailable, retain findings locally as pending publication and
continue independent authorized work.

## Changelog

> [!IMPORTANT]
> ## Rules
> 1. Follow [Keep a Changelog 2.0.0](https://keepachangelog.com/en/2.0.0/) and [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).
> 2. Keep stable sections and the current cumulative section for each in-progress target. Git tags preserve earlier preview snapshots.
> 3. Use `## [X.Y.Z] - YYYY-MM-DD (b1)` or `## [X.Y.Z] - YYYY-MM-DD (rc1)` for a preview. Update the date and stage in the same heading as the target progresses. For stable, use `## [X.Y.Z] - YYYY-MM-DD`. Append `[YANKED]` only for a yanked release. Keep all six categories under [Unreleased] and omit empty categories from released sections.
> 4. Include only curated changes with a notable effect on users or contributors. Exclude routine internal refactors, test-only work, and other changes without a user- or contributor-facing effect; resolving an issue alone does not require an entry.
> 5. File entries under their actual category. Start every breaking entry with `**Breaking:** 💥` under that category, identify affected users, and include migration guidance when possible.
> 6. Use the emoji mapping informed by [Gitmoji](https://github.com/carloscuesta/gitmoji) and [conventional-changelog-emoji](https://github.com/favoloso/conventional-changelog-emoji): ✨ Added, 🛠️ Changed, 🗑️ Deprecated, 🔥 Removed, 🐛 Fixed, and 🔒 Security.
> 7. Keep one cumulative section per target version. Describe the changes that ship since the previous stable release, including earlier preview changes still present in the current build. Each GitHub Release gets a snapshot of that section. Keep only the latest published beta download.
> 8. Use 🐛 Fixed only for defects in previously released behavior; describe new features under ✨ Added.
> 9. List [Unreleased] and stable major/minor `X.Y.0` releases in the TOC. Place version reference definitions immediately after the TOC. [Unreleased] compares the latest existing release tag with HEAD. For cumulative sections, compare the previous stable tag with the current tagged build. Use only existing tags.
>
> Local presentation exceptions: retain the project header, contribution guide link, TOC, and `<br>` / `---` layout; use emoji-prefixed category headings and the inline 💥 breaking marker; keep all six category headings under [Unreleased] even when empty; list only [Unreleased] and stable `X.Y.0` releases in the TOC; place reference definitions immediately after the TOC instead of at the bottom.

---

<br>

# Documentation and generated files

Update documentation when a change affects setup, commands, public APIs,
environment variables, saved formats, or user-visible workflows. Follow the
[changelog rules](#changelog) for notable changes.

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
and migration instructions for breaking changes. Follow the
[unfinished-work guidance](#issues-and-backlog) before closing the Pass. Coding agents must respect the user's commit and publication
permissions; a contribution guide does not grant release authorization.
