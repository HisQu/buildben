# Contributing to Buildben

Read the [development guide](docs/Development.md) for setup, checks, packaging,
installer verification, and release procedures.

## Quick start

1. Search [existing issues](https://github.com/HisQu/buildben/issues) and the
   [backlog](BACKLOG.md) for related work.
2. Follow the [development setup](docs/Development.md#development-setup) and
   [agent guidance](AGENTS.md) that apply to your work.
3. Run the relevant checks and use a pull request to explain the change and its
   verification.

## Issues and backlog

> [!CAUTION]
> These records can be published: Never record secrets, absolute paths, credentials, private host data, or speculative security claims. Use repository-relative source paths and full GitHub issue URLs. 


> [!IMPORTANT]
> 
> ## Rules
> 1) Preserve BACKLOG.md's header and TOC without changing them unnecessarily. 
> 1) Order planned Passes and entries by intended execution. Use priorities, dependencies, shared work, checks, and effort to group entries. Keep Deferred last.
> 1) Create or update an issue for real, actionable, out-of-scope work. Add a concise linked backlog entry when selected. Reorder, batch, reconcile, or remove entries when useful.
> 1) Search open and closed issues and the backlog for the same work. Keep two-way links between related issues using their full URLs. Preserve relevant closed history.
> 1) For a complete fix, use a closing issue reference in the PR to main and remove the backlog entry in the same change. Use an ordinary reference for a partial fix and keep unresolved scope open. Add a CHANGELOG.md entry only when the change has a notable user- or contributor-facing effect.
> 1) **Types:**
>       - **Bug risk**: Potential defect with concrete evidence, not yet confirmed.
>       - **Code smell**: Implementation, architectural, maintainability or clarity issue that is not currently a defect.
>       - **Docs drift**: Documentation is stale, incomplete, or inconsistent.
>       - **Tooling**: Issue with build, test, lint, type-check, and general slowdown of developer workflow.
>       - **Security**: Evidence-backed security risk. Use Question for uncertainty.
>       - **Question**: Design, behavior, or ownership uncertainty needing investigation.
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
> - **Evidence:** concrete observation
> - **Why not fixed now:** scope, risk, uncertainty, or user decision needed
> - **Suggested next step:** smallest reasonable follow-up. If applicable, reference related issues by URL.
> 
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Issue:** https://github.com/OWNER/REPO/issues/NUMBER
> - **Area:** `path/or/symbol`
> - ...
> 
> <br>
> 
> # Pass: short name
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
> 5. File entries under their actual category. Start every breaking entry with **Breaking:** 💥 under that category, identify affected users, and include migration guidance when possible.
> 6. Use the emoji mapping informed by [Gitmoji](https://github.com/carloscuesta/gitmoji) and [conventional-changelog-emoji](https://github.com/favoloso/conventional-changelog-emoji): ✨ Added, 🛠️ Changed, 🗑️ Deprecated, 🔥 Removed, 🐛 Fixed, and 🔒 Security.
> 7. Keep one cumulative section per target version. Describe the changes that ship since the previous stable release, including earlier preview changes still present in the current build. Each GitHub Release gets a snapshot of that section. Keep only the latest published beta download.
> 8. Use 🐛 Fixed only for defects in previously released behavior; describe new features under ✨ Added.
> 9. List [Unreleased] and stable major/minor `X.Y.0` releases in the TOC. Place version reference definitions immediately after the TOC. [Unreleased] compares the latest existing release tag with HEAD. For cumulative sections, compare the previous stable tag with the current tagged build. Use only existing tags.
>
> Local presentation exceptions: retain the project header, contribution guide link, TOC, and `<br>` / `---` layout; use emoji-prefixed category headings and the inline 💥 breaking marker; keep all six category headings under [Unreleased] even when empty; list only [Unreleased] and stable `X.Y.0` releases in the TOC; place reference definitions immediately after the TOC instead of at the bottom.
