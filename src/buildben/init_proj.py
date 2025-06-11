#!/usr/bin/env python3

from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from . import utils


# ================================================================== #
# === CLI wiring                                                     #
# ================================================================== #
def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Attach the init-proj sub-parser to the CLI aggregator."""

    DOC = """Scaffold a new src-layout Python project."""

    p: argparse.ArgumentParser = subparsers.add_parser(
        "init-proj",
        help=DOC,
        description=DOC,
    )
    p.add_argument("-n", "--name", required=True, help="Project name")
    p.add_argument(
        "-t",
        "--target-dir",
        default=".",
        help="Directory in which to create project",
    )
    p.add_argument(
        "-g", "--git", action="store_true", help="Initialise git repo"
    )
    p.add_argument(
        "-u", "--github-user", default="github-user", help="Github Username"
    )

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
    PR_ROOT: Path = Path(args.target_dir).expanduser().resolve() / args.name
    utils.warn_dir_overwrite(PR_ROOT)

    # =================================================================
    # === Directory tree
    # =================================================================

    directories: list[Path] = [
        PR_ROOT / "tests",
        PR_ROOT / "assets",
        PR_ROOT / "examples",
        PR_ROOT / "experiments",
        PR_ROOT / ".github" / "workflows",
        PR_ROOT / ".github" / "workflows_inactive",
        PR_ROOT / "src" / "utils",
        PR_ROOT / "src" / args.name,
        PR_ROOT / "src" / args.name / "data",
        PR_ROOT / "src" / args.name / "images",
    ]
    for dir in directories:
        dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # === Copy template files
    # =================================================================

    # > {<_template_filename>: <destination_filepath>}
    # fmt: off
    transfers: dict[str, Path] = {
        "_gitignore": PR_ROOT / ".gitignore",
        "_pyproject.toml": PR_ROOT / "pyproject.toml",
        "_envrc": PR_ROOT / ".envrc",
        "_justfile": PR_ROOT / "justfile",
        "_codecov.yml": PR_ROOT / ".github" / "workflows_inactive" / "codecov.yml",
        "_main.py": PR_ROOT / "src" / args.name / "main.py",
        "_utils_stdlib.py": PR_ROOT / "src" / "utils" / "stdlib.py",
        ### .IGNORE - Files are git-ignored until manually renamed:
        "_README.IGNORE.md": PR_ROOT / "README.IGNORE.md",
        "_flowchart.IGNORE.mmd": PR_ROOT / "assets" / "flowchart.IGNORE.mmd",
        "_classdiagram.IGNORE.mmd": PR_ROOT / "assets" / "classdiagram.IGNORE.mmd",
        "_diagram.IGNORE.puml": PR_ROOT / "assets" / "diagram.IGNORE.puml",
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
    if args.git:
        subprocess.run(["git", "init"], cwd=PR_ROOT, check=True)
        subprocess.run(["git", "add", "."], cwd=PR_ROOT, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial scaffold from buildben"],
            cwd=PR_ROOT,
            check=True,
        )

    # =================================================================
    # === Final message
    # =================================================================
    print(
        dedent(
            f"""
            ✅  {args.name} scaffold complete!

                cd "{PR_ROOT}"
                direnv allow        # trust .envrc
                just venv-reset     # set up .venv via direnv
            
            Happy hacking 🎉
            """
        )
    )
