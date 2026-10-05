# Integration records

## Merge 01: Buildben Worker-task 01

- Branch: `worker/261005-pypi_release_hard_disable-01-buildben_policy`.
- Covered worker range: `256db323410f4a399c6fe4566930d82813ca58ed..d546a58643516142f4b4122870722dbd653d5120`.
- Worker commits, both authored by `markur4`:
  - `211f38596bf991088c3fd8aae6ef5202bb847c22`: `fix(release): enforce committed PyPI policy`.
  - `d546a58643516142f4b4122870722dbd653d5120`: `Worker-task 261005: pin release preflight to workflow SHA`.
- Merge commit: `0cc308e6f259689cc277a846c9c9b1a91a66642a`, authored by `markur4`.
- Resulting `main` commit immediately after integration: `0cc308e6f259689cc277a846c9c9b1a91a66642a`.
- Changes: committed PyPI policy enforcement and workflow-SHA release preflight, with corresponding project templates, documentation, and tests.
- Merge outcome: `ort` strategy; no conflicts or conflict resolution; both reviewed worker commits integrated without additional code changes.
- Checks on merged `main`: `uv run --locked pytest tests/test_release_tooling.py tests/test_init_proj.py` passed all 55 tests; Ruff check and format passed; Pyright reported zero errors, warnings, or information; `git diff --check` and `just --summary` passed.
- Signing: merge commit contains an SSH signature header and signing remains enabled. Local signature verification is unavailable because `gpg.ssh.allowedSignersFile` is not configured.
- No push or PyPI action occurred.

Exact Analyst-authored Session-record commit message, identical to the merge message:

```text
fix(release): enforce committed PyPI policy (Worker-task 01: buildben_policy)
```
