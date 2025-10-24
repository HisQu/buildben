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
        help="Directory in which to create project",
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

    utils.create__init__(PROOT / "src" / args.name)
    utils.create__init__(
        PROOT / "src" / args.name / "utils",
        imports=["stdlib"],
        # < x = u.stdlib.my_function()
        # < import <my_project>.utils as u
    )

    # =================================================================
    # === Copy template files
    # =================================================================

    # > {<_template_filename>: <destination_filepath>}
    # fmt: off
    transfers: dict[str, Path] = {
        ### PR_ROOT:
        "_gitignore": PROOT / ".gitignore",
        "_pyproject.toml": PROOT / "pyproject.toml",
        "_envrc": PROOT / ".envrc",
        "_env.sh": PROOT / ".env.sh",
        "_justfile": PROOT / "justfile",
        ### PR_ROOT/.github:
        "_github_codecov.yml": PROOT / ".github" / "workflows_inactive" / "codecov.yml",
        ### PR_ROOT/src:
        "_src_main.py": PROOT / "src" / args.name / "main.py",
        "_src_env_boot.py": PROOT / "src" / args.name / "env_boot.py",
        ### PR_ROOT/src/utils:
        "_utils_stdlib.py": PROOT / "src" / args.name / "utils" / "stdlib.py",
        ### .IGNORE - Files are git-ignored until renamed manually:
        "_README.IGNORE.md": PROOT / "README.IGNORE.md",
        "_assets_flowchart.IGNORE.mmd": PROOT / "assets" / "flowchart.IGNORE.mmd",
        "_assets_classdiagram.IGNORE.mmd": PROOT / "assets" / "classdiagram.IGNORE.mmd",
        "_assets_diagram.IGNORE.puml": PROOT / "assets" / "diagram.IGNORE.puml",
    }
    # fmt: on

    tmpl_dir = Path(__file__).resolve().parent / "_templates_proj"
    utils.copy_templates(transfers=transfers, tmpl_dir=tmpl_dir)

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
                just insco         # Install dependencies
            
            Happy hacking 🎉
            """
        )
    )
