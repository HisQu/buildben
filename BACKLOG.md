# Backlog

Treat this as the parking lot for actionable problems discovered while working but intentionally left unresolved.


<br>

> [!CAUTION]
> This is git-tracked: Never record secrets, absolute paths, credentials, private host data, or speculative security claims. Use only relative paths. 


> [!IMPORTANT]
> 
> ## Rules
> 1) Do not remove or change this header and TOC without very good reason. 
> 1) Newest at the top.
> 1) Append a new entry only when the observation is real, actionable, not already listed, and out of scope for the current change. Do not modify `BACKLOG.md` when there is nothing useful to add.
> 1) If an issue is new and related to another issue, reference it in the `Suggested next step`. Do not create a new entry for the same problem. Place the reference in both entries (bi-directional).
> 1) If an issue was resolved, remove it and make an entry in the CHANGELOG.md.
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
> # YYYY-MM-DD 
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Area:**  `path/or/symbol`
> - **Observed while:** short context
> - **Evidence:** concrete observation
> - **Why not fixed now:** scope, risk, uncertainty, or user decision needed
> - **Suggested next step:** smallest reasonable follow-up. If applicable, reference related backlog items [here](#backlog).
> 
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Area:** `path/or/symbol`
> - ...
> 
> <br>
> 
> # YYYY-MM-DD
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Area:** `path/or/symbol`
> - ...
> ```



<br>

---

<br>

## Table Of Contents

1. [Backlog](#backlog)
   1. [Table Of Contents](#table-of-contents)
2. [2026-11-11](#2026-11-11)
   1. [P2 / E2 \[Tooling\] - *Exclude interpreter caches from release payloads*](#p2--e2-tooling---exclude-interpreter-caches-from-release-payloads)
2. [2026-10-30](#2026-10-30)
   1. [P3 / E2 \[Tooling\] - *Native installation proof remains pending*](#p3--e2-tooling---native-installation-proof-remains-pending)

<br>

---

<br>



# 2026-11-11

## P2 / E2 [Tooling] - *Exclude interpreter caches from release payloads*
- **Area:** `src/buildben_dev/packaging/release_stage.py`
- **Observed while:** comparing the downloaded 0.13.0 installer with native restaging after local Python 3.12/3.13 checks.
- **Evidence:** the published embedded ZIP has 56 members. Local restaging adds 13 members under `app_lifecycle/_support/__pycache__`; all 56 shared members are byte-identical. The published bundle is clean and its downloaded consumers pass.
- **Why not fixed now:** the released payload is correct. Cache filtering is a separate packaging follow-up; do not rewrite the published tag or assets.
- **Suggested next step:** exclude `__pycache__` and `.pyc` files when collecting support resources. Extend the existing release-asset tests to show that local interpreter caches do not change the staged payload. Inspect the parallel PersoDB stager before applying the same correction there.

<br>

# 2026-10-30

## P3 / E2 [Tooling] - *Native installation proof remains pending*
- **Area:** `.github/workflows/ci.yml`, `tests/test_release_install.py`, `tests/test_lifecycle.py`
- **Observed while:** implementing the AppRC-backed installation lifecycle from WSL Linux.
- **Evidence:** native Windows/macOS execution is not available in this session. Linux execution cannot establish Windows handle-sharing, registry integration, PowerShell/cmd bootstrap and actual-process removal handoff, or macOS native temporary-directory aliases.
- **Why not fixed now:** native Windows/macOS verification remains explicitly deferred. Current release authorization covers Linux only and does not authorize Windows executables from WSL, a new runner, or billing/security changes.
- **Suggested next step:** when native-platform work is authorized, exercise the maintained canonical/generated consumers, Windows cmd and PowerShell file/downloaded-text entries, and macOS staging aliases. Follow the [Windows procedure](README.md#windows-installer-verification-procedure) and [Unix staging procedure](README.md#unix-installer-staging-verification). This deferral does not block an explicitly authorized Linux-only release; Linux results do not establish native-platform readiness.
