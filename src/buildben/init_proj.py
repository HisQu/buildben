#!/usr/bin/env python3

from __future__ import annotations
import argparse
import re

# import shutil
import subprocess
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
    p.add_argument(
        "-g", "--git-init", action="store_true", help="Initialise git repo"
    )
    p.add_argument(
        "-u", "--github-user", default="github-user", help="Github Username"
    )
    # > Entrypoint, retrieved as args.func in cli.py
    p.set_defaults(func=_run)  # !! call _run(args) when chosen


# ================================================================== #
# === implementation                                                 #
# ================================================================== #
def _run(args: argparse.Namespace) -> None:

    ### Validate project name
    IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    if not IDENT_RE.match(args.name):
        sys.exit("💥  Project name must be a valid Python identifier")

    ### Project root
    # > .envrc and PROJ_ROOT do not exist yet, it's defined by user input:
    PROOT: Path = Path(args.target_dir).expanduser().resolve() / args.name
    utils.warn_dir_overwrite(PROOT)

    # =================================================================
    # === Directory tree
    # =================================================================

    directories: list[Path] = [
        PROOT / "tests",
        PROOT / "assets",
        PROOT / "examples",
        # PR_ROOT / "experiments",
        PROOT / ".github" / "workflows",
        PROOT / ".github" / "workflows_inactive",
        PROOT / "src" / args.name,
        PROOT / "src" / args.name / "utils",
        PROOT / "src" / args.name / "data",
        PROOT / "src" / args.name / "images",
    ]
    for dir in directories:
        dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # === Copy template files
    # =================================================================

    # > {<_template_filename>: <destination_filepath>}
    # fmt: off
    transfers: dict[str, Path] = {
        ### PR_ROOT:
        "_gitignore": PROOT / ".gitignore",
        "_pyproject.toml": PROOT / "pyproject.toml",
        "_.envrc": PROOT / ".envrc",
        "_.env.template": PROOT / ".env.template",
        "_justfile": PROOT / "justfile",
        ### PR_ROOT/.github:
        "_github-codecov.yml": PROOT / ".github" / "workflows_inactive" / "codecov.yml",
        "_github-CI_ubuntu_uv.yml": PROOT / ".github" / "workflows_inactive" / "CI_ubuntu_uv.yml",
        ### PR_ROOT/src:
        "_src-main.py": PROOT / "src" / args.name / "main.py",
        "_src-paths.py": PROOT / "src" / args.name / "paths.py",
        ### PR_ROOT/src/utils:
        "_utils-stdlib.py": PROOT / "src" / args.name / "utils" / "stdlib.py",
        "_utils-path_resolver.py": PROOT / "src" / args.name / "utils" / "path_resolver.py",
        ### .IGNORE - Files are git-ignored until renamed manually:
        "_README.IGNORE.md": PROOT / "README.IGNORE.md",
        "_assets-flowchart.IGNORE.mmd": PROOT / "assets" / "flowchart.IGNORE.mmd",
        "_assets-classdiagram.IGNORE.mmd": PROOT / "assets" / "classdiagram.IGNORE.mmd",
        "_assets-diagram.IGNORE.puml": PROOT / "assets" / "diagram.IGNORE.puml",
    }
    # fmt: on

    tmpl_dir = Path(__file__).resolve().parent / "_templates_proj"
    utils.copy_templates(transfers=transfers, tmpl_dir=tmpl_dir)

    # =================================================================
    # === __init__.py files
    # =================================================================
    utils.create_init_dot_py(PROOT / "src" / args.name)
    # > This is copied
    utils.create_init_dot_py(
        PROOT / "src" / args.name / "utils",
        imports=["stdlib", "path_resolver"],
        flatten_functions=True,
        # < x = u.stdlib.my_function()
        # < import <my_project>.utils as u
    )

    # =================================================================
    # === Placeholder substitution
    # =================================================================
    placeholders = {
        "<my_project>": args.name,
        "{my_project}": args.name,
        "<github_username>": args.github_user,
        "{github_username}": args.github_user,
    }

    utils.substitute_placeholders(
        filepaths=list(transfers.values()), placeholders=placeholders
    )

    # =================================================================
    # === Optional git init
    # =================================================================
    if args.git_init:
        utils.git_init(PROOT)

    # =================================================================
    # === Final message
    # =================================================================
    print(
        dedent(
            f"""
            ✅  {args.name} scaffold complete!
            
            👉 Next Steps:
                cd "{PROOT}"
                direnv allow       # Trust .envrc
                just               # List available recipes
            
            Happy hacking 🎉
            """
        )
    )
