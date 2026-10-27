# Repository conventions

Before making changes, read [Contributing](CONTRIBUTING.md) and follow its shared
conventions. Consult the relevant [Development](docs/Development.md) guides.

## Release policy
- Treat the committed `RELEASE_PYPI` value in `justfile` as a hard gate. When it is `"false"`, do not recommend or run a manual PyPI publish or retry command.
- Manual PyPI publication requires `RELEASE_PYPI := "true"` in both the current committed `justfile` and the requested tag's committed `justfile`. A `just --set` override does not satisfy either check.
- The manual workflow checks the selected workflow ref and target tag before it requests the PyPI environment or OIDC token. GitHub Release creation on a valid tag remains available when PyPI is disabled.

## Repo routing and project rules
- Follow [Working conventions](CONTRIBUTING.md#working-conventions) and the
  [repository layout](docs/Development.md#repository-routing).
- Inspect the existing owner and shared helpers before adding an implementation;
  warn the user when documented paths appear stale.
- Check [BACKLOG.md](BACKLOG.md) and assess related durable work for the pass.
- Keep one authoritative active checklist beside its plan. Before closing a
  pass, transfer unfinished work according to the shared contribution rules.

## Documentation rules
- Follow the canonical [documentation rules](docs/README.md#documentation-rules),
  including component names, navigation, and
  [installation instructions](docs/README.md#installation-instructions).

## README maintenance
- Adapt in place; never replace the README with a generic README. Before editing,
  follow [README maintenance](CONTRIBUTING.md#readme-maintenance), including the
  approval boundary for substantial redesign.

## Verification
- Review the diff for duplicate helpers, naming drift, unnecessary abstractions, and regressions.
- Run the project’s relevant lint, type-check, and test commands before considering the task done.
- Before Windows installer work, follow the canonical
  [Windows installer verification procedure](docs/Development.md#windows-installer-verification-procedure).
- From WSL, never launch native Windows verification executables, directly or
  through helpers: this includes PowerShell, Windows Python/pytest, `cmd.exe`,
  and Windows `uv`. Use independent native Windows CI, not a Windows virtual
  environment or executable launched from WSL.
- For Unix installer changes, follow the
  [Unix staging verification procedure](docs/Development.md#unix-installer-staging-verification).
  Preserve lifecycle link checks and distinguish actual installer proof from
  the generated direct-package smoke.

## User Decisions
- Never answer questions on the user's behalf.
- Do not treat recommended options, defaults, timeouts, or auto-resolution as user approval or user preference.
- If a user decision is required, ask and wait for the user’s explicit answer.
