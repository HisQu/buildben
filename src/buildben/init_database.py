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

CMD_NAME = "init-database"  # < Name of the CLI-command
CMD_ALIASES = ["data"]  # < Alias shortcut of the CLI-command
DOC = f"Scaffolds a new data repository with similair layout as any Python project. Aliases: {CMD_ALIASES}"

### TODO: This is identical to init_proj.py. Make a common base class or function to avoid duplication.
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
    raise NotImplementedError("init_data is not implemented yet. Please use init_proj instead.")

    # =================================================================
    # === Copy template files (from init_proj.py)
    # =================================================================
    # > {<_template_filename>: <destination_filepath>}
    # fmt: off
    transfers: dict[str, Path] = {
        ### PR_ROOT:
        "_gitignore": PROOT / ".gitignore",
        "_pyproject.toml": PROOT / "pyproject.toml",
        "_envrc": PROOT / ".envrc",
        "_justfile": PROOT / "justfile",
        ### PR_ROOT/.github:
        "_github_codecov.yml": PROOT / ".github" / "workflows_inactive" / "codecov.yml",
        ### PR_ROOT/src:
        "_src_main.py": PROOT / "src" / args.name / "main.py",
        "_src_env.py": PROOT / "src" / args.name / "env.py",
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
    # === Write .gitattributes
    # =================================================================

    """
    How to handle data in git:
    - .gitattributes
        - https://git-scm.com/docs/gitattributes
    *.csv   diff=none   merge=union   -text
    *.json  diff=none   merge=union   -text
    *.xlsx  binary
    *.npy   binary
    
    *.pickle binary
    *.txt   -text
    *.md    -text
    
    How exactly does this track changes?
    
    - textconv
        - What's textconv exactly?
    
    - git lfs track "*.csv" "*.xlsx"
    
    
    prompt:
    Alright! Now let's tackle git: I have lots of excel, .csvs, JSON, .npy.  files etc.. They're not big, a couple of KB or MB, but still, git treats them with too much rigor like code, so changes to data confuse my other git-tools.Are there any options git uses to treat them differently but still enable version control? What are my options and what are best practices?
    """

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
