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


def _project_directories(project_root: Path, name: str) -> list[Path]:
    """Return directories required by the project scaffold.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :return: Directories to create before copying templates.
    """
    return [
        project_root / "tests",
        project_root / "assets",
        project_root / "examples",
        project_root / "docs",
        project_root / "docs" / "assets",
        project_root / ".codex",
        project_root / ".github" / "workflows",
        project_root / ".github" / "workflows_inactive",
        project_root / "src" / name,
        project_root / "src" / name / "cli",
        project_root / "src" / name / "config",
        project_root / "src" / name / "utils",
        project_root / "src" / name / "data",
        project_root / "src" / name / "images",
    ]


def _project_template_transfers(project_root: Path, name: str) -> dict[str, Path]:
    """Map project template filenames to generated output paths.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :return: Template transfer mapping consumed by ``utils.copy_templates``.
    """
    return {
        "_gitignore": project_root / ".gitignore",
        "_pyproject.toml": project_root / "pyproject.toml",
        "_.envrc": project_root / ".envrc",
        "_.envrc.private": project_root / ".envrc.private",
        "_justfile": project_root / "justfile",
        "_AGENTS.md": project_root / "AGENTS.md",
        "_CHANGELOG.md": project_root / "CHANGELOG.md",
        "_TODO.md": project_root / "TODO.md",
        "_docs-README.md": project_root / "docs" / "README.md",
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
        "_github-CI_ubuntu_uv.yml": project_root
        / ".github"
        / "workflows_inactive"
        / "CI_ubuntu_uv.yml",
        "_src-main.py.tmpl": project_root / "src" / name / "main.py",
        "_src-__main__.py.tmpl": project_root / "src" / name / "__main__.py",
        "_src-cli-app.py.tmpl": project_root / "src" / name / "cli" / "app.py",
        "_src-config-app.py.tmpl": project_root / "src" / name / "config" / "app.py",
        "_src-config-init.py.tmpl": project_root
        / "src"
        / name
        / "config"
        / "__init__.py",
        "_src-config-owners.py.tmpl": project_root
        / "src"
        / name
        / "config"
        / "owners.py",
        "_src-config-env.shared": project_root
        / "src"
        / name
        / "config"
        / ".env.shared",
        "_utils-stdlib.py.tmpl": project_root / "src" / name / "utils" / "stdlib.py",
        "_README.IGNORE.md": project_root / "README.md",
        "_assets-flowchart.IGNORE.mmd": project_root
        / "assets"
        / "flowchart.IGNORE.mmd",
        "_assets-classdiagram.IGNORE.mmd": project_root
        / "assets"
        / "classdiagram.IGNORE.mmd",
    }


def _project_placeholders(name: str, github_user: str) -> dict[str, str]:
    """Return placeholder replacements for project templates.

    :param name: Import package name.
    :param github_user: GitHub username shown in generated metadata.
    :return: Placeholder replacement mapping.
    """
    scaffold_date = dt.date.today().isoformat()
    return {
        "<my_project>": name,
        "{my_project}": name,
        "<project_name>": name,
        "{project_name}": name,
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
    }


def _create_project_directories(project_root: Path, name: str) -> None:
    """Create the directory tree for a generated project.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :return: None.
    """
    for directory in _project_directories(project_root, name):
        directory.mkdir(parents=True, exist_ok=True)


def _create_init_files(project_root: Path, name: str) -> None:
    """Create generated package ``__init__.py`` files.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
    :return: None.
    """
    package_root = project_root / "src" / name
    utils.create_init_dot_py(package_root)
    utils.create_init_dot_py(package_root / "cli", imports=["app"])
    utils.create_init_dot_py(
        package_root / "utils",
        imports=["stdlib"],
        flatten_functions=True,
    )


def _print_success(project_root: Path, name: str) -> None:
    """Print the final scaffold success message.

    :param project_root: Root directory of the generated project.
    :param name: Import package name.
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


# ================================================================== #
# === implementation                                                 #
# ================================================================== #
def _run(args: argparse.Namespace) -> None:
    _validate_project_name(args.name)
    project_root = _project_root(args.target_dir, args.name)
    utils.warn_dir_overwrite(project_root)
    _create_project_directories(project_root, args.name)

    transfers = _project_template_transfers(project_root, args.name)
    tmpl_dir = Path(__file__).resolve().parent / "_templates_proj"
    utils.copy_templates(transfers=transfers, tmpl_dir=tmpl_dir)
    _create_init_files(project_root, args.name)
    utils.substitute_placeholders(
        filepaths=list(transfers.values()),
        placeholders=_project_placeholders(args.name, args.github_user),
    )

    if args.git_init:
        utils.git_init(project_root)

    _print_success(project_root, args.name)
