# Repository conventions

## Repo routing
- Warn me if the paths below appear outdated.
- Reuse existing helpers and utilities before adding new helper functions.
- Check these modules first:
  - `<my_project>.utils`
- If a helper is broadly reusable, place it in the appropriate shared module.

## Project rules
- Do not duplicate helpers or re-implement existing utilities without checking first.
- Update `README.md` if a change affects usage or setup.
- Add minimal `__main__` demo code only when it improves discoverability or manual testing.

## Verification
- Review the diff for duplicate helpers, naming drift, unnecessary abstractions, and regressions.
- Run the project’s relevant lint, type-check, and test commands before considering the task done.