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
