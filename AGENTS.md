# Repository guidance

Read [Contributing](CONTRIBUTING.md) before repository work and follow its
links to the relevant [development procedures](docs/Development.md).

GitHub Issues hold durable work. `BACKLOG.md` orders planned Passes.
`TODO.md` beside `PLAN.md` holds the active Pass checklist. `CHANGELOG.md`
records notable delivered changes. `CONTRIBUTING.md` owns the shared rules
for these records.

Follow the canonical [Windows installer verification procedure](README.md#windows-installer-verification-procedure) before continuing Windows installer work. From WSL, never launch native Windows test executables (including PowerShell, Windows Python/pytest, `cmd.exe`, or Windows `uv`), directly or through helpers.

For Unix installer changes, follow the [Unix staging verification procedure](README.md#unix-installer-staging-verification). Exercise the real consumer smoke, including staging aliases, without weakening lifecycle link checks.
