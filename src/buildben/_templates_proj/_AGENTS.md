# Repository conventions

## Release policy
- Treat the committed `RELEASE_PYPI` value in `justfile` as a hard gate. When it is `"false"`, do not recommend or run a manual PyPI publish or retry command.
- Manual PyPI publication requires `RELEASE_PYPI := "true"` in both the current committed `justfile` and the requested tag's committed `justfile`. A `just --set` override does not satisfy either check.
- The manual workflow checks the selected workflow ref and target tag before it requests the PyPI environment or OIDC token. GitHub Release creation on a valid tag remains available when PyPI is disabled.

## Repo routing
- Warn me if the paths below appear outdated.
- Reuse existing helpers and utilities before adding new helper functions.
- Check these modules first:
  - `<my_project>.config`
  - `<my_project>.utils`
  - `apprc`
  - `apprc.cli`
- If a helper is broadly reusable, place it in the appropriate shared module.
- Put long-form docs in `docs/`:
  - procedures in `docs/How-To-User-Guides.md`
  - maintainer workflow in `docs/Development.md`
  - exact paths, commands, and public names in `docs/References.md`
  - component explanations in `docs/Explanations.md`
  - complete application examples in `docs/EXAMPLES.md`
- Put CLI behavior in `<my_project>.cli.app`; keep `<my_project>.main` as a
  thin public entry point wrapper.
- Check the TODO.md and assess if your task is related to any issues and should be resolved as part of your pass.

## Project rules
- Do not duplicate helpers or re-implement existing utilities without checking first.
- App configuration belongs in `<my_project>.config.sections`. Keep fields in focused `rc.Config` classes with `rc.field(...)` declarations, assemble them in `config.bundle`, and declare the shared `APP_RC` in `config.app`. Import declarations and classes directly from their modules. Use `rc.cli.mount_config_cli` to mount configuration commands; runtime values come from `state.resolved`.
- CLI behavior belongs in `<my_project>.cli.app`; keep `<my_project>.main` as a thin public entry point wrapper.
- Use stdlib `logging` for app-owned logs; AppRC integration should start from `import apprc as rc`.
- Import `<my_project>`-owned utility helpers through the facade: `import <my_project>.utils as ut`.
- Use explicit `ut.` prefixes for local utilities.
- For facade `__init__.py` files, prefer clean batch re-export imports plus file-level `# ruff: noqa: F401`; do not use redundant `symbol as symbol` aliases solely to satisfy Ruff.
- Update `README.md` or `docs/` if a change affects usage, setup, CLI behavior, public APIs, environment variables, or user-visible workflows.
- Add minimal `__main__` demo code only when it improves discoverability or manual testing.
- If a test needs a lighter setup, add or reuse a dedicated test helper instead of widening production code to `Any`.
- If a boundary is truly dynamic, model that boundary explicitly; do not probe strict domain objects defensively.

## Documentation rules
- Follow [Documentation](docs/README.md#documentation-rules), including its component-name table.
- Use the exact page names: Documentation, Explanations, How-to user guides, References, Examples, and Development.
- Explain each component's job, inputs, outputs, and connections before introducing more complex combinations.
- Define a component name before using it; reuse that name rather than inventing synonyms.
- Link relevant words inside paragraphs and tables to exact chapters. Connect explanations, implementations, and references in both directions.
- Do not use generic further-reading lists or related-link callouts.
- Give each guide explicit prerequisites, complete files or labeled excerpts, commands, and expected results. Keep examples independent.
- In all six `docs/` pages, put every H2 under a topical H1. Nest every H2 under that H1 in the table of contents, and put a standalone `<br>` before each topical H1. The generated documentation test enforces this rule.
- Use sentence-case headings and GitHub callouts for their stated purposes.
- Preserve Graphigs figure standards and regenerate assets through their source builders.
- Update CHANGELOG.md for user-visible changes. Add TODO.md entries only for actionable unresolved work, after checking for duplicates.

## Installation rules
- Keep the root README concise and installation-first. Under `Installation`, put the H3 heading `One-line install` before `Install from a cloned repository`. Under each, label platform commands with `For Linux & macOS` and `For Windows` headings.
- The one-line installer selects the latest stable GitHub release source archive by default. Public downloads use curl on Unix or native PowerShell HTTP on Windows and do not require GitHub CLI.
- BuildBen and generated installers accept `--github-client gh` for authenticated GitHub requests; they do not fall back when authentication fails. Link https://cli.github.com/ and document `gh auth login` plus `gh auth setup-git` when authenticated access is relevant.
- Private VCS dependencies independently require working Git credentials. Public release downloads and curl never inherit gh credentials.
- Keep cloned-repository development separate from installer options: use Python and `pip install -e .`, or use `uv sync` when desired. Installers do not provide `--git` or `--dev` modes.
- Standard GitHub releases contain exactly one wheel and one source archive, with release notes in the release body. Do not document installation bundles, platform archives, manifests, or permanent runtime exports.
- Normal release workflows reuse one successful full CI run for the exact commit. The six native CI cells exercise the source installer; the release job runs one Python 3.12 wheel install smoke.

## Verification
- Review the diff for duplicate helpers, naming drift, unnecessary abstractions, and regressions.
- Run the project’s relevant lint, type-check, and test commands before considering the task done.

## User Decisions
- Never answer questions on the user's behalf.
- Do not treat recommended options, defaults, timeouts, or auto-resolution as user approval or user preference.
- If a user decision is required, ask and wait for the user’s explicit answer.
