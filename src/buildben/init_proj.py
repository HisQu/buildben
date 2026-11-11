#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import re

# import shutil
import sys
from pathlib import Path
from textwrap import dedent

from . import utils

# ================================================================== #
# === CLI wiring                                                     #
# ================================================================== #

CMD_NAME = "init-proj"  # < Name of the CLI-command
CMD_ALIASES = ["proj"]  # < Alias shortcut of the CLI-command
DOC = f"Scaffolds a new src-layout Python project. Aliases: {CMD_ALIASES}"
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _add_my_parser(subparsers: argparse._SubParsersAction) -> None:
    """Attach the init-proj sub-parser to the CLI aggregator."""

    p: argparse.ArgumentParser = subparsers.add_parser(
        name=CMD_NAME,
        aliases=CMD_ALIASES,
        help=DOC,
        description=DOC,
    )
    p.add_argument("name", help="Project name")
    p.add_argument(
        "-t",
        "--target-dir",
        default=".",
        help="(Parent-)Directory in which to create a project-directory",
    )
    p.add_argument("-g", "--git-init", action="store_true", help="Initialise git repo")
    p.add_argument("-u", "--github-user", default="github-user", help="Github Username")
    p.add_argument(
        "--frontend",
        choices=("react",),
        default=None,
        help="Include an optional React frontend",
    )
    # > Entrypoint, retrieved as args.func in cli.py
    p.set_defaults(func=_run)  # !! call _run(args) when chosen


def _validate_project_name(name: str) -> None:
    """Validate that a project name can be imported as a Python package.

    :param name: Requested project/package name.
    :return: None.
    """
    if not IDENT_RE.match(name):
        sys.exit("💥  Project name must be a valid Python identifier")


def _project_root(target_dir: str, name: str) -> Path:
    """Resolve the destination directory for a new scaffold.

    :param target_dir: Parent directory supplied by the caller.
    :param name: Project directory name.
    :return: Absolute project root path.
    """
    return Path(target_dir).expanduser().resolve() / name


def _project_directories(
    project_root: Path, name: str, *, frontend: bool
) -> list[Path]:
    """Return directories required by the project scaffold.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :param frontend: Whether to include the React application directories.
    :return: Directories to create before copying templates.
    """
    directories = [
        project_root / "tests",
        project_root / "tests" / "support_source_transport",
        project_root / "assets",
        project_root / "examples",
        project_root / "docs",
        project_root / "docs" / "assets",
        project_root / ".codex",
        project_root / ".github" / "workflows",
        project_root / ".github" / "workflows_inactive",
        project_root / "src" / name,
        project_root / "src" / f"{name}_distr" / "payload" / "app_lifecycle",
        project_root / "src" / f"{name}_distr" / "artifacts",
        project_root / "src" / f"{name}_dev" / "packaging",
        project_root / "src" / name / "cli",
        project_root / "src" / name / "config",
        project_root / "src" / name / "config" / "sections",
        project_root / "src" / name / "utils",
        project_root / "src" / name / "data",
        project_root / "src" / name / "images",
    ]
    if frontend:
        directories.extend(
            (
                project_root / "frontend",
                project_root / "frontend" / "src",
                project_root / "frontend" / "src" / "test",
            )
        )
    return directories


def _project_template_transfers(
    project_root: Path, name: str, *, frontend: bool
) -> dict[str, Path]:
    """Map project template filenames to generated output paths.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :param frontend: Whether to copy the React application templates.
    :return: Template transfer mapping consumed by ``utils.copy_templates``.
    """
    transfers = {
        "_gitattributes": project_root / ".gitattributes",
        "_gitignore": project_root / ".gitignore",
        "_pyproject.toml": project_root / "pyproject.toml",
        "_.envrc": project_root / ".envrc",
        "_.envrc.private": project_root / ".envrc.private",
        "_justfile": project_root / "justfile",
        "_AGENTS.md": project_root / "AGENTS.md",
        "_CONTRIBUTING.md": project_root / "CONTRIBUTING.md",
        "_CHANGELOG.md": project_root / "CHANGELOG.md",
        "_BACKLOG.md": project_root / "BACKLOG.md",
        "_docs-README.md": project_root / "docs" / "README.md",
        "_docs-EXAMPLES.md": project_root / "docs" / "EXAMPLES.md",
        "_docs-How-To-User-Guides.md": project_root / "docs" / "How-To-User-Guides.md",
        "_docs-Development.md": project_root / "docs" / "Development.md",
        "_docs-References.md": project_root / "docs" / "References.md",
        "_docs-Explanations.md": project_root / "docs" / "Explanations.md",
        "_docs-assets-docs-reading-map.svg": project_root
        / "docs"
        / "assets"
        / "docs-reading-map.svg",
        "_.codex_config.toml": project_root / ".codex" / ".codex_config.toml",
        "_github-codecov.yml": project_root
        / ".github"
        / "workflows_inactive"
        / "codecov.yml",
        "_github-ci.yml": project_root / ".github" / "workflows" / "ci.yml",
        "_github-diagnostics.yml": project_root
        / ".github"
        / "workflows"
        / "diagnostics.yml",
        "_github-release.yml": project_root / ".github" / "workflows" / "release.yml",
        "_src-main.py.tmpl": project_root / "src" / name / "main.py",
        "_src-__main__.py.tmpl": project_root / "src" / name / "__main__.py",
        "_src-cli-app.py.tmpl": project_root / "src" / name / "cli" / "app.py",
        "_src-config-app.py.tmpl": project_root / "src" / name / "config" / "app.py",
        "_src-config-init.py.tmpl": project_root
        / "src"
        / name
        / "config"
        / "__init__.py",
        "_src-config-sections-init.py.tmpl": project_root
        / "src"
        / name
        / "config"
        / "sections"
        / "__init__.py",
        "_src-config-sections-app.py.tmpl": project_root
        / "src"
        / name
        / "config"
        / "sections"
        / "app.py",
        "_src-config-bundle.py.tmpl": project_root
        / "src"
        / name
        / "config"
        / "bundle.py",
        "_src-config-apprc.defaults.env": project_root
        / "src"
        / name
        / "config"
        / "apprc.defaults.env",
        "_utils-stdlib.py.tmpl": project_root / "src" / name / "utils" / "stdlib.py",
        "_src-dev-packaging-release_assets.py.tmpl": project_root
        / "src"
        / f"{name}_dev"
        / "packaging"
        / "release_assets.py",
        "_src-dev-packaging-release_notes.py.tmpl": project_root
        / "src"
        / f"{name}_dev"
        / "packaging"
        / "release_notes.py",
        "_src-dev-packaging-release_manifest.py.tmpl": project_root
        / "src"
        / f"{name}_dev"
        / "packaging"
        / "release_manifest.py",
        "_src-dev-packaging-release_stage.py.tmpl": project_root
        / "src"
        / f"{name}_dev"
        / "packaging"
        / "release_stage.py",
        "_src-dev-packaging-install_smoke.py.tmpl": project_root
        / "src"
        / f"{name}_dev"
        / "packaging"
        / "install_smoke.py",
        "_src-distr-make_artifacts.py.tmpl": project_root
        / "src"
        / f"{name}_distr"
        / "make_artifacts.py",
        "_src-distr-payload-init.py.tmpl": project_root
        / "src"
        / f"{name}_distr"
        / "payload"
        / "app_lifecycle"
        / "__init__.py",
        "_src-distr-payload-install.py.tmpl": project_root
        / "src"
        / f"{name}_distr"
        / "payload"
        / "app_lifecycle"
        / "install.py",
        "_src-distr-payload-uninstall.py.tmpl": project_root
        / "src"
        / f"{name}_distr"
        / "payload"
        / "app_lifecycle"
        / "uninstall.py",
        "_src-distr-payload-actions.py.tmpl": project_root
        / "src"
        / f"{name}_distr"
        / "payload"
        / "app_lifecycle"
        / "actions.py",
        "_MANIFEST.in": project_root / "MANIFEST.in",
        "_tests-test_package.py.tmpl": project_root
        / "tests"
        / f"test_{name}_package.py",
        "_tests-support_source_transport-server.py.tmpl": project_root
        / "tests"
        / "support_source_transport"
        / "server.py",
        "_tests-support_source_transport-sitecustomize.py.tmpl": project_root
        / "tests"
        / "support_source_transport"
        / "sitecustomize.py",
        "_tests-support_source_transport-gh": project_root
        / "tests"
        / "support_source_transport"
        / "gh",
        "_tests-support_source_transport-gh.py.tmpl": project_root
        / "tests"
        / "support_source_transport"
        / "gh.py",
        "_tests-support_source_transport-gh.cmd": project_root
        / "tests"
        / "support_source_transport"
        / "gh.cmd",
        "_tests-test_documentation.py.tmpl": project_root
        / "tests"
        / "test_documentation.py",
        "_README.md": project_root / "README.md",
        "_assets-flowchart.IGNORE.mmd": project_root
        / "assets"
        / "flowchart.IGNORE.mmd",
        "_assets-classdiagram.IGNORE.mmd": project_root
        / "assets"
        / "classdiagram.IGNORE.mmd",
    }
    if frontend:
        frontend_root = project_root / "frontend"
        transfers.update(
            {
                "_frontend-justfile": frontend_root / "justfile",
                "_frontend-package.json": frontend_root / "package.json",
                "_frontend-bun.lock": frontend_root / "bun.lock",
                "_frontend-index.html": frontend_root / "index.html",
                "_frontend-tsconfig.json": frontend_root / "tsconfig.json",
                "_frontend-eslint.config.js": frontend_root / "eslint.config.js",
                "_frontend-vite.config.ts": frontend_root / "vite.config.ts",
                "_frontend-src-App.tsx": frontend_root / "src" / "App.tsx",
                "_frontend-src-main.tsx": frontend_root / "src" / "main.tsx",
                "_frontend-src-App.test.tsx": frontend_root / "src" / "App.test.tsx",
                "_frontend-src-test-setup.ts": frontend_root
                / "src"
                / "test"
                / "setup.ts",
            }
        )
    return transfers


def _pascal_project_name(name: str) -> str:
    """Convert a valid package name into a class-name stem.

    :param name: Valid Python package identifier selected for the scaffold.
    :return: PascalCase form suitable for generated public class names.
    """
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def _project_placeholders(
    name: str, github_user: str, *, frontend: bool
) -> dict[str, str]:
    """Return placeholder replacements for project templates.

    :param name: Import package name.
    :param github_user: GitHub username shown in generated metadata.
    :param frontend: Whether to enable frontend recipes, CI, and ignores.
    :return: Placeholder replacement mapping.
    """
    scaffold_date = dt.date.today().isoformat()
    pascal_name = _pascal_project_name(name)
    distribution = re.sub(r"[-_.]+", "-", name).lower()
    frontend_ci_job = ""
    if frontend:
        frontend_ci_job = (
            Path(__file__).resolve().parent
            / "_templates_proj"
            / "_frontend-ci.yml.tmpl"
        ).read_text(encoding="utf-8")
    return {
        "<my_project>": name,
        "{my_project}": name,
        "<project_name>": name,
        "{project_name}": name,
        "<MyProject>": pascal_name,
        "{MyProject}": pascal_name,
        "<MY_PROJECT>": name.upper(),
        "{MY_PROJECT}": name.upper(),
        "<PROJECT_NAME>": name.upper(),
        "{PROJECT_NAME}": name.upper(),
        "<github_username>": github_user,
        "{github_username}": github_user,
        "<github_user>": github_user,
        "{github_user}": github_user,
        "<bb_date>": scaffold_date,
        "{bb_date}": scaffold_date,
        "<bb_today>": scaffold_date,
        "{bb_today}": scaffold_date,
        "<scaffold_date>": scaffold_date,
        "{scaffold_date}": scaffold_date,
        "<initial_version>": "0.1.0",
        "{initial_version}": "0.1.0",
        "<distribution_name>": distribution,
        "<frontend_just_module>": (
            "[group('Frontend')]\nmod front 'frontend/justfile'" if frontend else ""
        ),
        "<frontend_ci_job>": frontend_ci_job,
        "<frontend_gitignore>": (
            "frontend/node_modules/\n"
            "frontend/dist/\n"
            "frontend/coverage/\n"
            "frontend/.vitest/"
            if frontend
            else ""
        ),
    }


def _create_project_directories(
    project_root: Path, name: str, *, frontend: bool
) -> None:
    """Create the directory tree for a generated project.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :param frontend: Whether to create the React application directories.
    :return: None.
    """
    for directory in _project_directories(project_root, name, frontend=frontend):
        directory.mkdir(parents=True, exist_ok=True)


def _create_init_files(project_root: Path, name: str) -> None:
    """Create generated package ``__init__.py`` files.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :return: None.
    """
    package_root = project_root / "src" / name
    utils.create_init_dot_py(package_root)
    utils.create_init_dot_py(project_root / "src" / f"{name}_dev")
    utils.create_init_dot_py(project_root / "src" / f"{name}_dev" / "packaging")
    utils.create_init_dot_py(project_root / "src" / f"{name}_distr")
    utils.create_init_dot_py(project_root / "src" / f"{name}_distr" / "payload")
    utils.create_init_dot_py(
        project_root / "src" / f"{name}_distr" / "payload" / "app_lifecycle"
    )
    utils.create_init_dot_py(package_root / "cli", imports=["app"])
    utils.create_init_dot_py(
        package_root / "utils",
        imports=["stdlib"],
        flatten_functions=True,
    )


def _print_success(project_root: Path, name: str, *, frontend: bool) -> None:
    """Print the final scaffold success message.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :param frontend: Whether to show frontend next steps.
    :return: None.
    """
    print(
        dedent(
            f"""
            ✅  {name} scaffold complete!
            
            👉 Next Steps:
                cd "{project_root}"
                direnv allow       # Trust .envrc
                just               # List available recipes
            
            Happy hacking 🎉
            """
        )
    )
    if frontend:
        print(
            "Frontend next steps:\n"
            "    just front sync\n"
            "    just front dev\n"
            "    just --list front"
        )


# ================================================================== #
# === implementation                                                 #
# ================================================================== #
def _run(args: argparse.Namespace) -> None:
    _validate_project_name(args.name)
    frontend = args.frontend == "react"
    project_root = _project_root(args.target_dir, args.name)
    utils.warn_dir_overwrite(project_root)
    _create_project_directories(project_root, args.name, frontend=frontend)

    transfers = _project_template_transfers(project_root, args.name, frontend=frontend)
    tmpl_dir = Path(__file__).resolve().parent / "_templates_proj"
    utils.copy_templates(transfers=transfers, tmpl_dir=tmpl_dir)
    _create_init_files(project_root, args.name)
    utils.substitute_placeholders(
        filepaths=[
            destination
            for template, destination in transfers.items()
            if template not in {"_frontend-package.json", "_frontend-bun.lock"}
        ],
        placeholders=_project_placeholders(
            args.name, args.github_user, frontend=frontend
        ),
    )

    if args.git_init:
        utils.git_init(project_root)

    _print_success(project_root, args.name, frontend=frontend)
