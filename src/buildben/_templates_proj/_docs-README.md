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
| [Development](Development.md) | Change source, verify behavior, and prepare releases. |

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
| [Installers](References.md#installer-reference) | `src/{my_project}_dev/distribution` | Platform scripts for online Git installs, checkout sync, and local wheel installs. |

## Documentation rules

These rules apply to the root README, all documents, examples, and generated
package descriptions. Contributors and coding agents must follow them.

### Installation instructions

- Keep the root README concise and put installation before usage. Under `Installation`, use the H3 headings `Install online` and `Install from a checkout`.
- Online one-liners work only after the repository has been pushed to GitHub. Fetch scripts with authenticated `gh api` so private repositories work with existing credentials. Require GitHub CLI `gh` and Git access, and do not add an authentication tutorial.
- Stop on a failed or empty script fetch before executing any response. Bash examples must guard `bash -c` with a successful, nonempty `gh api` command substitution; PowerShell examples must check `$LASTEXITCODE` and reject empty content before `Invoke-Expression`.
- Checkout instructions use `python -m venv` and `python -m pip install -e .`, so users can install without uv. Mention uv as optional.
- Keep the offline bundle placeholder in the root README as an HTML comment. Do not remove it or make it active until the repository has a bundle production process that creates and tests the offline files.
- Do not say that offline bundles are available before that process exists. Avoid generic upgrade warnings.
- Keep platform installer code in `src/{my_project}_dev/distribution`; the root install scripts are thin shortcuts. See the [installer reference](References.md#installer-reference) for modes and options.

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

### Review

- In the six pages in `docs/`, keep the document-title H1 above the table of
  contents. Add topical H1 sections below it and put every H2 under one of them.
  List each topical H1 at the top level of the table of contents and every H2
  exactly once beneath its H1, in document order. The title does not need a
  table-of-contents link; H3 headings may stay out of the compact list.
- Put a standalone `<br>` before the first topical H1 and between later H1
  sections. Do not add spacers between H2 sections. The root README, changelog,
  and TODO keep their own heading layouts. The generated documentation test
  checks this rule in CI.
- Review prose for undefined terms, naming drift, unsupported claims, and lists
  that fail to explain relationships. Link checks cannot judge explanation quality.
- Run the [verification commands](Development.md#verification) and the documented
  examples. Verify source precedence and which files each operation changes.
- Preserve [Graphigs styling](References.md#figure-visual-tokens). Regenerate
  generated assets from their source rather than editing their outputs.
