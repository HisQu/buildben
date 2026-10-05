# Orchestrator decisions

## Session scope

1. Treat the committed `RELEASE_PYPI` value as a hard gate for every publication path. False means no PyPI action. Do not configure a PersoDB publisher or publish to PyPI.
2. Update Buildben's own release files and project templates first. Then use a generated Buildben project to guide PersoDB changes, retaining only PersoDB-specific names and settings.
3. Preserve the user's uncommitted PersoDB `INPUT/` files and the separate `buildben-scaffold` checkout. Work in task-specific worktrees.
4. Include the root README and maintainer docs wherever they repeat the unsafe manual-publish guidance. Add tests for disabled and enabled policies.

## Implementation decisions

- Require exact committed `true` before the local manual command authenticates or contacts GitHub, and verify the requested tag's committed policy.
- Make GitHub manual workflow preflight read and validate policy before the publishing job can request PyPI credentials. Disabled policy must skip publication with a clear notice.
- Keep normal tagged GitHub Release behavior and enabled PyPI publication available.
- After each complete worker range, obtain Analyst review before integration because the change gates release credentials and spans scripts, workflows, tests, and docs.

## Worker-task 01 handoff

- Branch: `worker/261005-pypi_release_hard_disable-01-buildben_policy`
- Worktree: [redaction: local absolute path] (basename: `buildben-policy`)
- Base: `256db323410f4a399c6fe4566930d82813ca58ed`
- Tip: `211f38596bf991088c3fd8aae6ef5202bb847c22`
- Range: `256db323410f4a399c6fe4566930d82813ca58ed..211f38596bf991088c3fd8aae6ef5202bb847c22`
- Worker reports 52 focused tests, Ruff, Pyright, `git diff --check`, and `just --summary` passed. The SSH signature block is present, but `git verify-commit` cannot validate it without `gpg.ssh.allowedSignersFile`.
- Analyst review is required before integration; no merge has occurred.

## Analyst-task 02: Buildben code review

Dispatched to `gpt-6.1-sol` at medium effort. Review the complete Worker-task 01 range read-only. Do not integrate until its verdict is approved.

## Analyst-task 02 verdict

The verdict is `changes requested`. The full Analyst review is recorded in `analyses.md`. Its P2 finding is that the manual preflight resolves mutable `github.ref` at job time. It must check out and evaluate policy at immutable `${{ github.sha }}` and add a branch-advance regression test. Do not integrate the current range.

## Worker-task 01 follow-up

Sent the exact P2 correction to the existing worker. Keep the original commit `211f385` unchanged, add a follow-up commit, and send the complete corrected range for Analyst follow-up review before integration.

## Worker-task 01 corrected handoff

- Follow-up commit: `d546a58643516142f4b4122870722dbd653d5120`, authored by `markur4`.
- Full range: `256db323410f4a399c6fe4566930d82813ca58ed..d546a58643516142f4b4122870722dbd653d5120`.
- Follow-up range: `211f38596bf991088c3fd8aae6ef5202bb847c22..d546a58643516142f4b4122870722dbd653d5120`.
- The root and scaffold preflights now checkout and evaluate `${{ github.sha }}`, confirm it matches `HEAD`, and use `github.ref` only for diagnostics. The added regression covers false policy at the dispatch SHA with a true branch tip and true target tag.
- Worker reports 51 tests passed and 4 skipped, Ruff, Pyright, `git diff --check`, and `just --summary` passed. Signing remains enabled; signature verification remains unavailable without `gpg.ssh.allowedSignersFile`.

## Analyst-task 03: Buildben follow-up review

Dispatched to the same `gpt-6.1-sol` Analyst at medium effort to review the full corrected range. No integration until the verdict is approved.

## Analyst-task 03 verdict and integration decision

The Analyst approved the full corrected range and supplied the integration message `fix(release): enforce committed PyPI policy (Worker-task 01: buildben_policy)`. The current local `main`, `origin/main`, and fetched remote `main` all resolve to the Worker-task base. Integrate this approved range into Buildben `main` with a no-fast-forward merge and the exact Analyst-authored message. Preserve SSH signing.

## Analyst-task 04: Buildben Merge Summary

The Merge Summary Analyst confirmed that commits `211f385` and `d546a58` from the approved Worker-task 01 range were integrated without conflict or additional code edits in merge commit `0cc308e6f259689cc277a846c9c9b1a91a66642a`. Post-merge validation passed: 55 focused tests, Ruff check/format, Pyright with zero diagnostics, `git diff --check`, and `just --summary`. SSH signing remained enabled; local signature verification is unavailable without `gpg.ssh.allowedSignersFile`. No push or PyPI action occurred. The exact Analyst-authored Session-record message is `fix(release): enforce committed PyPI policy (Worker-task 01: buildben_policy)`; see [the Merge Summary](merges.md#merge-01-buildben-worker-task-01).

## Worker-task 02 scope: PersoDB policy

Apply the merged Buildben scaffold behavior to PersoDB from a task-specific worktree based on `873f1aae860b3ec1fc4421b64bc5017de4f70817`. Retain PersoDB-specific package and release details. Leave the root checkout's `INPUT/` changes and the separate `buildben-scaffold` checkout untouched. Required Analyst review precedes integration. Do not push, dispatch releases, or publish to PyPI.
