# Documentation

- [Find the right page](#find-the-right-page)
  - [Start here](#start-here)
  - [Choose a document](#choose-a-document)
- [Documentation conventions](#documentation-conventions)
  - [Component names](#component-names)
  - [Documentation rules](#documentation-rules)

<br>

# Find the right page

## Start here

`{my_project}` starts as a Python package with a Typer command line and AppRC
configuration. Learn its [command-line application](Explanations.md#command-line-application)
and [config sections](Explanations.md#config-sections) before adding settings or
commands. Then [initialize storage](How-To-User-Guides.md#initialize-storage)
and inspect the values used by the generated application.

The [storage-only example](EXAMPLES.md#storage-only-application) is the default
setup. The other examples show changes you can make after understanding it.
Replace the starter message with your application's settings and describe new
components here as you implement them.

## Choose a document

| Document | Purpose |
| --- | --- |
| [Explanations](Explanations.md) | Define the application's components and explain their connections. |
| [How-to user guides](How-To-User-Guides.md) | Complete one task with explicit prerequisites and expected results. |
| [References](References.md) | Look up exact commands, files, environment variables, and Python names. |
| [Examples](EXAMPLES.md) | Compare complete setups and run them. |
| [Contributing](../CONTRIBUTING.md) | Shared conventions, the normal setup and checks, and submission expectations. |
| [Development](Development.md) | Detailed development, verification, and maintenance guides. |

<br>

# Documentation conventions

## Component names

Keep these names fixed in every document. Add project-specific components as
actual application behavior is implemented.

| Name | Implementation | Definition |
| --- | --- | --- |
| [Command-line application](Explanations.md#command-line-application) | `{my_project}.cli.app` | The Typer command tree run by the console and module entrypoints. |
| [`AppRC`](Explanations.md#apprc) | `APP_RC` in `config/app.py` | One application declaration that registers settings and enables storage. |
| [Config section](Explanations.md#config-sections) | `AppSettings` in `config/sections/app.py` | A class containing related typed settings. |
| [Config field](Explanations.md#config-sections) | `rc.field(...)` | One setting's environment key, default, and documentation. |
| [`ResolvedConfig`](Explanations.md#resolvedconfig) | `state.resolved` in runtime commands | Values read for one invocation, used to build settings. |
| [Config bundle](Explanations.md#config-bundle) | `{MyProject}Config` in `config/bundle.py` | A dataclass containing the application's config sections. |
| [Storage](Explanations.md#storage) | A registered data directory | Persistent application data and a storage-specific dotenv file. |
| [Storage registry](Explanations.md#storage) | `apprc.toml` | Names, paths, and the saved default storage. |
| [AppRC directory](Explanations.md#configuration-files) | Directory chosen by `{MY_PROJECT}_APPRC_DIR` | Home of the storage registry and an optional user dotenv. |
| [ConfigManager](Explanations.md#configuration-tools) | `APP_RC.manage()` | Shared operations for setup, inspection, editing, and storage management. |
| [Config CLI](Explanations.md#configuration-tools) | `{my_project} config ...` | Configuration commands mounted on the application. |
| [Config editor](Explanations.md#configuration-tools) | `{my_project} config edit` | Terminal interface for inspecting layers and editing saved overrides. |
| [Installers](References.md#installer-reference) | `src/{my_project}_dev/distribution` | Canonical installers for latest/specified releases and pinned `--main` snapshots, using public or authenticated transports. |

## Documentation rules

These rules apply to the root README, all documents, examples, and generated
package descriptions. Contributors and coding agents must follow them.

### Installation instructions

- Put installation before usage. Under `Installation`, keep `One-Line Install` before `Install from a Cloned Repository`, preserving the root README's existing heading hierarchy and layout. Keep platform labels such as `For Linux & macOS` and `For Windows` with their commands; installer examples may remain commented out. Follow [README maintenance](../CONTRIBUTING.md#readme-maintenance) rather than deleting useful content to make the README concise.
- The one-line installer bootstraps from the repository's default branch. It installs the latest stable release by default; `--version VERSION` selects a release and `--main` selects a single pinned commit from remote `main` with its committed `uv.lock`. Main requires GitHub access but no release or Actions artifact; it may be unreleased code whose CI has not passed. See the [installer reference](References.md#installer-reference).
- Public installation uses curl on Unix or native PowerShell HTTP on Windows and does not require GitHub CLI. `--github-client gh` uses authenticated GitHub CLI requests without fallback.
- Link https://cli.github.com/ and document `gh auth login` and `gh auth setup-git` where authenticated access is needed. Private VCS dependencies require separate working Git credentials.
- Cloned-repository instructions use `python -m venv` and `python -m pip install -e .`, so users can install without uv. Mention uv as optional.
- GitHub releases contain one standard wheel and one source archive; do not describe installer bundles, platform archives, manifests, or permanent runtime exports.
- Keep platform installer code in `src/{my_project}_dev/distribution`; root install scripts are thin shortcuts.

### Names and explanations

- Use the document labels in [Choose a document](#choose-a-document) exactly.
  Do not introduce alternatives such as Recipes for How-to user guides or
  Architecture for Explanations.
- Use the [component names](#component-names) consistently. Define a component
  before using its name in instructions. Do not invent synonyms for variation.
- Teach the smallest working application first. Introduce configuration files,
  storage, and integrations only after the components they depend on.
- In Explanations, state what each component is, why it exists, what it receives
  or produces, and how it connects to other named components. Use concrete verbs
  such as reads, creates, calls, validates, and writes.
- A sentence listing undefined technical nouns is not an explanation. Use a
  specific input, action, and result when the relationship is otherwise unclear.
- Use task headings in How-to user guides. Introduce unfamiliar terms in the
  opening explanation, rather than expecting readers to know them from a title.
- Describe implemented behavior. Mark future plans explicitly and keep migration
  history in migration instructions and the changelog.

### Links and examples

- Link the relevant word or phrase within its paragraph or table cell, as in
  "The [storage registry](Explanations.md#storage) remembers the directory."
- Link components to exact Explanations sections, operations to How-to user guides,
  exact APIs or commands to References, and complete setups to Examples.
- Connect the documents in both directions through useful inline links. Link
  the first useful occurrence in a section rather than every repetition.
- Do not collect ordinary cross-links in Related links callouts or generic
  further-reading paragraphs. GitHub callouts are for prerequisites, warnings,
  context, or optional advice that needs emphasis.
- Make task examples independent. Supply imports, declarations, filenames,
  commands, prerequisites, and expected results. Identify excerpts explicitly.
- Examples must explain when to choose each setup and how its parts work together.
  Keep complete executable applications in `examples` and link to their files.
- Use relative links with section anchors. Check links, anchors, and tables of
  contents after edits. Preserve existing published anchors when practical.

### README navigation

- Keep the root README's Documentation section as a curated navigation tree
  grouped by using the project and contributing or maintaining it.
- Keep shared contribution rules and the normal quick start in
  [Contributing](../CONTRIBUTING.md); keep detailed procedures in
  [Development](Development.md). Do not copy their command blocks into the README.
- Update incoming links in the same change when adding, moving, renaming, or
  removing a document or linked section.
- Include useful starting points and frequently needed destinations, not every
  subsection. Use relative paths, direct section anchors, and short descriptions.
- Preserve the established grouping, nesting, and presentation. Routine entry
  and destination updates are expected; redesign requires an explicit request.
- This intentional navigation tree is not a generic further-reading collection;
  ordinary cross-links in prose should still appear where readers need them.

### Callouts

Use sentence-case headings in new documentation and `<details>` for long
examples, while preserving the existing root documents' designs.

| Marker | Use |
| --- | --- |
| `[!TIP]` | Optional workflow advice. |
| `[!NOTE]` | Helpful background. |
| `[!IMPORTANT]` | Required prerequisite or architecture rule. |
| `[!WARNING]` | Deprecated behavior, temporary bugs, or costly operations. |
| `[!CAUTION]` | Destructive or security-relevant actions. |

Place the marker alone on its blockquote line; GitHub ignores custom titles.

### Review

- In the six pages in `docs/`, keep the document-title H1 above the table of
  contents. Add topical H1 sections below it and put every H2 under one of them.
  List each topical H1 at the top level of the table of contents and every H2
  exactly once beneath its H1, in document order. The title does not need a
  table-of-contents link; H3 headings may stay out of the compact list.
- Put a standalone `<br>` before the first topical H1 and between later H1
  sections. Do not add spacers between H2 sections. The root README, CONTRIBUTING,
  changelog, and TODO keep their own heading layouts. The generated documentation
  test checks the six docs pages' outlines in CI and ordinary relative links in
  README, CONTRIBUTING, AGENTS, and the docs pages.
- Review prose for undefined terms, naming drift, unsupported claims, and lists
  that fail to explain relationships. Link checks cannot judge explanation quality.
- Run the [normal checks](../CONTRIBUTING.md#run-checks), follow the detailed
  [verification guide](Development.md#verification), and execute changed examples.
  Verify source precedence and which files each operation changes.
- Preserve [Graphigs styling](References.md#figure-visual-tokens). Regenerate
  generated assets from their source rather than editing their outputs.
