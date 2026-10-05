# Analyst and review reports

## Analyst-task 01: PyPI policy cause analysis

The analysis found that `RELEASE_PYPI := "false"` gated normal tag publication only. The local `publish-pypi` recipe and manual workflow bypassed that gate; `release-push` and the development guide told maintainers to use the manual path; tests expected dispatch while the setting was false. The failed manual attempt then reached PyPI and failed because no trusted publisher existed. That missing publisher explains the job error, not why publication was attempted. Do not configure a PersoDB publisher or make a PyPI release as part of this fix.

Recommended enforcement: fail before GitHub auth/network in the local recipe unless committed policy is exactly `true`; validate the target tag policy too. Add a manual workflow preflight with no PyPI environment or OIDC permission, then gate the publishing job on its output. Make release output conditional and update docs, scaffold agent guidance, and tests. Buildben's root and project scaffold both contain the same defect.

Evidence also showed that PersoDB v0.11.1 completed normally with both PyPI jobs skipped. The observed failed manual attempts were for v0.10.5. See the prior Analyst-task report in the conversation for run references and source lines.

Analyst-task count through planning: 1. Token counts unavailable.

## Analyst-task 02: preliminary review finding

Review is still in progress. The reviewer reproduced a likely blocker: the manual workflow preflight resolves mutable `github.ref` when the job runs. If the dispatch ref advances from a false policy to a true policy before that job evaluates it, the preflight can authorize PyPI. The reviewer is completing the exact finding and required correction; do not integrate until the final verdict.

## Analyst-task 02: Buildben code review

Verdict: changes requested

Reviewed the complete range `256db323410f4a399c6fe4566930d82813ca58ed..211f38596bf991088c3fd8aae6ef5202bb847c22` on `worker/261005-pypi_release_hard_disable-01-buildben_policy`, containing commit `211f385` (`fix(release): enforce committed PyPI policy`).

1. **P2: Pin the manual preflight to the workflow run's commit.**
   `.github/workflows/release.yml` line 151 explicitly checks out `${{ github.ref }}`, then resolves that mutable ref at lines 162–171. The scaffold repeats this at `src/buildben/_templates_proj/_github-release.yml` line 143.

   A queued run or rerun dispatched from a commit containing `RELEASE_PYPI := "false"` can check a later branch commit containing `"true"` and authorize publication. I reproduced this by executing the workflow's extracted Bash against a temporary repository: the dispatch SHA contained false, the branch subsequently advanced to true, and the target tag contained true. The script exited successfully with `publish_pypi=true`.

   Explicitly supplying a branch ref prevents checkout from retaining its default event SHA; this follows the [official checkout v5 implementation](https://raw.githubusercontent.com/actions/checkout/v5/src/input-helper.ts). Thus the preflight can check a different commit from the one supplying the running workflow.

   **Required fix:** In both workflows, check out `${{ github.sha }}` for `workflow_dispatch` and evaluate the policy at that immutable commit. Retain `github.ref` for diagnostic labels if useful. Update the assertions at `tests/test_init_proj.py` line 845 and their scaffold equivalents. Add a behavioral regression test where the dispatch commit is false but the branch advances to true; publication must remain disabled. Preserve an enabled true/true case.

Checks and results:

- **52 focused tests passed**, using the reviewed worktree's `src` through `PYTHONPATH`. An initial run imported the shared virtual environment's editable checkout and failed four scaffold assertions; correcting the source path resolved those failures.
- Ruff checking and formatting checks passed for both changed test files.
- `git diff --check` passed; the worktree remains clean.
- Root and scaffold committed-policy helpers, release recipes, and manual preflight blocks are identical.
- The local four-policy matrix passes, including rejection before any fake `gh` call when either committed policy is false.
- Independently verified that `RELEASE_PYPI=true` in the environment and `just --set RELEASE_PYPI true` cannot change the helper's result for a committed false assignment.
- The preflight has only `contents: read`, with no PyPI environment or OIDC permission. The publishing job depends on successful preflight and its explicit true output.
- Normal GitHub Release creation retains its existing path. Enabled automatic and manual publication retain their artifact upload/download behavior.
- `release-push` now reports committed policy and suppresses manual publication guidance when false. README, changelog, scaffold guidance, and development guide consistently document the intended gate.
- Pyright and `just --summary` were reported passing by the worker; I did not rerun them.

Residual risks and uncertainty:

- No live GitHub workflow, environment approval, OIDC issuance, or PyPI upload was exercised.
- Existing historical workflow versions can retain their earlier behavior; this change protects runs using the corrected workflow.
- Repository administrators can change workflows, policies, tags, and release assets. This review addresses enforcement through the maintained release paths.

Review text suitable for `analyses.md`:

> Verdict: changes requested. Reviewed the complete range `256db323410f4a399c6fe4566930d82813ca58ed..211f38596bf991088c3fd8aae6ef5202bb847c22`. Local committed-policy enforcement, credential ordering, root/scaffold parity, release guidance, and enabled local publication pass review. One P2 finding blocks integration: manual preflight checks mutable `github.ref` rather than the dispatch commit. Extracted workflow Bash authorized publication after a false dispatch commit's branch advanced to true. Pin both workflow checkouts and policy reads to the immutable dispatch SHA, update structural assertions, and add a branch-advance regression test. Independently verified 52 focused tests, Ruff checking/formatting, and diff whitespace checks. No project files were changed or publication attempted. Re-review the corrected complete range before integration or the PersoDB port.

No integration commit message is supplied because approval is pending.

Analyst-task count: 1 for this review; Session records show 2 through this dispatch. Token counts unavailable.

## Analyst-task 03: Buildben follow-up code review

Verdict: approved

Reviewed the complete range `256db323410f4a399c6fe4566930d82813ca58ed..d546a58643516142f4b4122870722dbd653d5120` on `worker/261005-pypi_release_hard_disable-01-buildben_policy`, including commits `211f385` and `d546a58`.

No actionable findings or blocking findings remain. The change is suitable for integration as Buildben's canonical release policy.

The prior P2 finding is fully corrected:

- `.github/workflows/release.yml` line 151 checks out `${{ github.sha }}`. Policy evaluation resolves that SHA and verifies that checkout `HEAD` matches it. `github.ref` appears only in diagnostics.
- The scaffold applies the same correction in `src/buildben/_templates_proj/_github-release.yml` line 143.
- `tests/test_release_tooling.py` line 157 exercises a false policy at the run SHA, a branch advanced to true, and a true target tag. It checks out the original SHA and requires `publish_pypi=false`. The companion case requires true/true to produce `publish_pypi=true`.
- I ran that regression against the original vulnerable preflight script in a temporary repository. It correctly failed after observing `publish_pypi=true`, demonstrating that the test detects the original defect.

The explicit SHA checkout follows the [official checkout v5 implementation](https://raw.githubusercontent.com/actions/checkout/v5/src/input-helper.ts), which treats a SHA input as the commit to retrieve.

Checks and results:

- **55 focused tests passed, with no skips**, using the reviewed worktree's `src`.
- Ruff checking and formatting checks passed for both changed test files.
- `git diff --check` and `just --summary` passed; the worktree remains clean.
- Root and scaffold preflight scripts, committed-policy helpers, and release recipes remain aligned.
- Local publication requires both committed policies to be true before calling `gh`. The policy matrix and enabled path pass.
- Preflight retains only `contents: read`. The publishing job requires its successful true output before entering the PyPI environment with OIDC permission.
- Normal tagged GitHub Releases and explicitly enabled PyPI publication retain their existing behavior.
- README, changelog, scaffold guidance, development guide, and conditional `release-push` output match the policy.
- Pyright was reported passing by the worker; I did not repeat it.

Residual risks and uncertainty: no live workflow, environment approval, OIDC issuance, or PyPI upload was exercised. Historical workflow versions retain their historical behavior. No project files were changed during review.

Analyst-authored review text:

> Verdict: approved. Reviewed the complete range `256db323410f4a399c6fe4566930d82813ca58ed..d546a58643516142f4b4122870722dbd653d5120`, including the original policy change and SHA-pinning correction. The prior P2 finding is resolved in both root and scaffold workflows. The branch-advance regression passes with the corrected script and detects the original vulnerable script. No blocking findings remain. Independently verified 55 focused tests without skips, Ruff checking/formatting, diff whitespace checks, and just summary. Local committed-policy enforcement, credential ordering, scaffold parity, release guidance, and enabled release behavior remain sound. No publication or project changes occurred during review.

Analyst-authored integration commit message:

```text
fix(release): enforce committed PyPI policy (Worker-task 01: buildben_policy)
```

Analyst-task count: 1 for this follow-up; 3 total through this dispatch. Token counts unavailable.

## Analyst-task 05: PersoDB code review (changes requested)

[Paraphrase of the Analyst report.] The full PersoDB change range has two blockers. **P1:** an unqualified Git/tag name can resolve to a same-named branch if the exact tag is false or missing, so policy checks must use exact `refs/tags/<tag>` refs and fail closed. **P2:** manual preflight checks a policy value, but the privileged publisher later resolves mutable Release metadata and downloads mutable assets; publication must consume the exact bytes validated by preflight. Preserve release-bundle behavior while fixing both. Do not integrate until the corrected full range is reviewed.

Analyst-task count: 1 for this review; 5 total through this dispatch. Token counts unavailable.

## Analyst-task 06: immutable release-snapshot design

[Paraphrase of the Analyst report.] Bind the workflow to the exact tag commit. In an unprivileged preflight, validate the expected wheel and source archive, calculate hashes, record release/tag/commit identities in a manifest, recheck the tag, then upload the validated package snapshot as an Actions artifact. Only authorize the privileged publisher after artifact upload succeeds. The publisher must download by artifact ID and verify the manifest and exact package set before publishing those captured files. Repository tag protection is still needed to prevent a later administrator move from changing the meaning of the tag; this is a residual repository setting, not a code guarantee.

Analyst-task count: 1 for this design analysis; 6 total through this dispatch. Token counts unavailable.

## Analyst-task 07: Buildben endpoint follow-up review (changes requested)

[Paraphrase of the Analyst report.] Reviewed the complete Buildben Worker-task 03 range. The documented GitHub release-asset download endpoint was constructed incorrectly as `/releases/$release_id/assets/$asset_id`; use `/repos/$GITHUB_REPOSITORY/releases/assets/$asset_id`. Strengthen the mock and assertions to require the exact endpoint and both snapshot downloads. Do not integrate until this is corrected and the full range is reviewed again.

Analyst-task count: 1 for this review; 7 total through this dispatch. Token counts unavailable.

## Analyst-task 08: Buildben corrected follow-up review (approved)

[Paraphrase of Analyst-task 08 review.]

Verdict: approved. Reviewed the complete corrected range `c6bcc9009955bdd785626b584903574126f79ea7..6d495879ec516c30535459cfaeac18cc42ded2ed`, including both commits. The root and project scaffold use `/repos/$GITHUB_REPOSITORY/releases/assets/$asset_id`; tests assert the exact requests and reject the prior route. The approved safeguards remain: exact tag-policy resolution, preflight package hashes and identity manifest, tag recheck, artifact upload before authorization, and privileged download by artifact ID followed by manifest/package verification. Automatic release and PyPI sections are unchanged from the range base.

The Analyst independently ran 62 tests (4 skipped), Ruff, Pyright (zero diagnostics), full-range `git diff --check`, the false local policy check, and a negative mutation check for the old endpoint. No live workflow or publication was exercised. The documented residual risk is that administrators can move/delete the tag after preflight; tag protection is not established by this code change.

Analyst-authored integration message, to use verbatim:

```text
Merge Worker-task 03: enforce Buildben tag policy and validated PyPI snapshots
```

Analyst-task count: 1 for this follow-up; 8 total through this dispatch. Token counts unavailable.

## Analyst-task 09: Buildben Merge Summary

[Paraphrase of Analyst-task 09 Merge Summary.]

The Merge Summary reports that the approved Worker-task 03 range was integrated without conflicts in merge commit `8c937020a5e1c7776f9d0d7f069a1de571eb7019`. Its two worker commits were authored by `markur4`. The integrated change binds manual PyPI publication to the checked tag snapshot using package hashes and recorded release/tag/commit identities. Post-merge validation passed: 66 tests, Ruff format and lint, Pyright with zero diagnostics, root and rendered-scaffold workflow YAML parsing, `just --list`, `just --evaluate RELEASE_PYPI` returning `false`, and `git diff --check`. SSH signature verification remains unavailable because `gpg.ssh.allowedSignersFile` is unset. Local `main` is ahead of `origin/main`; no push, workflow dispatch, release, or PyPI publication occurred.

Exact Analyst-authored Session-record commit message:

```text
Merge Worker-task 03: enforce Buildben tag policy and validated PyPI snapshots
```

Analyst-task count: 1 for this Merge Summary; 9 total through this dispatch. Token counts unavailable.

## Analyst-task 10: PersoDB full-range code review

Verdict: changes requested

[Paraphrase of Analyst-task 10 review.]

Reviewed the complete frozen range `873f1aae860b3ec1fc4421b64bc5017de4f70817..ac91a530a8b7bce3c9b1124cfa3650c7f08a11f3`, containing commits `e8c247b68518c330390125fc55de3dbde579aefa` and `ac91a530a8b7bce3c9b1124cfa3650c7f08a11f3`, and all eight changed files.

1. **P2: The changelog omits the breaking manual-publication requirement and migration.** `CHANGELOG.md:68` leaves Breaking changes empty. `CHANGELOG.md:92` records the policy change only under Fixed, without identifying affected maintainers or explaining migration. Previously, maintainers could manually publish an existing release while committed policy was false; this range requires committed true policy in both the current/workflow-run commit and target tag. That changes release-tool usage.

   The required `repository-engineering` skill says to “make breaking changes explicit under `### 💥 Breaking changes`” and requires affected users and migration instructions. Canonical Buildben already documents this same requirement under Breaking changes.

   **Required correction:** Add an explicit Breaking entry identifying maintainers who previously used manual publication with false policy. Explain that an intentionally PyPI-enabled release requires committing true before preparing its release tag, using a workflow-run commit and target tag that both contain true, and running the local command from a committed true HEAD. Existing false-policy tags remain ineligible. Keep PersoDB's current flag false. The Fixed entry can retain the enforcement and snapshot details without duplicating the migration.

No additional blocking implementation findings were identified. The review found that exact `refs/tags/<tag>` resolution fails closed for missing tags, non-commit targets, and same-named branches; local false policy stops before GitHub authentication; and manual preflight evaluates the immutable workflow-run SHA and exact tag commit before authorization. Preflight captures and validates only the selected PersoDB wheel and source archive, hashes them, records identities, rechecks the remote tag, and uploads before authorizing publication. The privileged publisher uses the artifact ID, verifies manifest identity, exact files, and hashes, and publishes only the captured packages. PersoDB's package-specific filter excludes installation bundles; automatic jobs, GitHub Release attachments, and installation-bundle jobs are unchanged from the range base. `AGENTS.md`, README, and development guidance prohibit manual publication or retry while committed policy is false.

Independent checks passed: 71 focused release and installer tests; full suite 446 passed, 2 skipped, 62 warnings; Ruff format and lint for changed test files; Pyright zero diagnostics; workflow YAML parsing; full-range `git diff --check`; and `just --evaluate RELEASE_PYPI` returning `false`. Worker-reported checks included the same full suite, all-project Ruff and Pyright, `just --summary`, and clean worktree. No live workflow or publication was performed.

Residual risk: administrators can move or delete the tag after preflight. Publication remains bound to the captured snapshot, but repository protections are needed to preserve tag identity. Repository tag settings and signature trust were not verified.

Integration approval and its commit message are withheld pending the changelog correction and follow-up review.

Analyst-task count: 1 for this review; 10 total through this dispatch. Token counts unavailable.

## Analyst-task 11: PersoDB corrected full-range review

Verdict: approved

[Paraphrase of Analyst-task 11 review.]

Reviewed the complete corrected range `873f1aae860b3ec1fc4421b64bc5017de4f70817..fc26508ccb73a654ab019de9c7ff8fc7e83233be`, containing commits `e8c247b68518c330390125fc55de3dbde579aefa`, `ac91a530a8b7bce3c9b1124cfa3650c7f08a11f3`, and `fc26508ccb73a654ab019de9c7ff8fc7e83233be`.

No blocking findings remain. Analyst-task 10's P2 is resolved at `CHANGELOG.md:70`: the entry appears under Breaking changes, names affected maintainers, and explains the committed true-policy migration for both workflow-run and exact target-tag commits, the local committed-HEAD requirement, and continued ineligibility of false-policy tags. It matches canonical Buildben, while PersoDB's committed default remains false.

The correction changes only `CHANGELOG.md`; the other seven files remain byte-for-byte unchanged from the previously reviewed tip. The prior review findings remain resolved: exact tag resolution fails closed; false policy blocks local and manual publication; preflight checks immutable commit identities; the privileged publisher consumes only the validated artifact-ID snapshot; and ordinary GitHub Releases and installation bundles remain intact.

Independent follow-up checks: 40 release tests passed; changelog parsing returned latest release `0.11.1`; `just --evaluate RELEASE_PYPI` returned `false`; full-range `git diff --check` passed; frozen tip and clean worktree confirmed. The previous independent validation remains applicable: 446 tests passed, 2 skipped, 62 warnings; 71 focused release/installer tests; Ruff, Pyright, and workflow YAML parsing. These broader checks were not rerun for the documentation-only correction.

Residual risk is unchanged: administrators can move/delete a tag after preflight. Publication remains bound to the captured snapshot, but repository protections are needed to preserve tag identity. Repository settings and signature trust remain unverified. No live workflow or publication occurred.

Analyst-authored integration commit message:

```text
Merge Worker-task 02: enforce PersoDB policy and validated PyPI snapshots
```

Analyst-task count: 1 for this follow-up review; 11 total through this dispatch. Token counts unavailable.
