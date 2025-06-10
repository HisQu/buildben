#!/usr/bin/env python3

from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Attach the init-proj sub-parser to the CLI aggregator."""

    DOC = """Scaffold a new src-layout Python project."""

    p: argparse.ArgumentParser = subparsers.add_parser(
        "init-proj",  # < the command name typed on the shell
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
        "-u",
        "--github-user",
        default="github-user",
        help="Github Username",
    )

    p.set_defaults(func=_run)  # !! call _run(args) when chosen


def _run(args: argparse.Namespace) -> None:

    ### Validate project name
    IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    if not IDENT_RE.match(args.name):
        sys.exit("💥  Project name must be a valid Python identifier")

    ### Resolve path to project root
    pr_root: Path = Path(args.target_dir).expanduser().resolve() / args.name
    # > Warn user if project root already exists
    if pr_root.exists():
        answer = input(
            f"⚠️  {pr_root} exists and files may be overwritten. Continue? [y/N] "
        ).lower()
        if answer not in {"y", "yes"}:
            sys.exit("Aborted by user")

    # =================================================================
    # === Directory tree
    # =================================================================

    directories: list[Path] = [
        pr_root / "tests",
        pr_root / "assets",
        pr_root / "examples",
        pr_root / "experiments",
        pr_root / ".github" / "workflows",
        pr_root / ".github" / "workflows_inactive",
        pr_root / "src" / args.name,
        pr_root / "src" / args.name / "data",
        pr_root / "src" / args.name / "images",
    ]
    for dir in directories:
        dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # === Copy template files
    # =================================================================
    script_dir = Path(__file__).resolve().parent
    tmpl_dir = script_dir / "templates"

    # > {<_template_filename>: <destination_filepath>}
    # fmt: off
    copies: dict[str, Path] = {
        "_gitignore": pr_root / ".gitignore",
        "_pyproject.toml": pr_root / "pyproject.toml",
        "_envrc": pr_root / ".envrc",
        "_justfile": pr_root / "justfile",
        "_codecov.yml": pr_root / ".github" / "workflows_inactive" / "codecov.yml",
        "_main.py": pr_root / "src" / args.name / "main.py",
        ### These are git-ignored until manually renamed (marked by bb_template.)
        "_README.bb_template.md": pr_root / "README.bb_template.md",
        "_flowchart.bb_template.mmd": pr_root / "assets" / "flowchart.bb_template.mmd",
        "_classdiagram.bb_template.mmd": pr_root / "assets" / "classdiagram.bb_template.mmd",
        "_diagram.bb_template.puml": pr_root / "assets" / "diagram.bb_template.puml",
    }
    # fmt: on

    for tmpl_fn, dst_fp in copies.items():
        tmpl_fp = tmpl_dir / tmpl_fn
        shutil.copy2(tmpl_fp, dst_fp, follow_symlinks=False)

    # =================================================================
    # === Placeholder substitution
    # =================================================================
    placeholders = {
        "<my_project>": args.name,
        "{my_project}": args.name,
        "<github_username>": args.github_user,
        "{github_username}": args.github_user,
    }

    for fp in list(copies.values()):
        text = fp.read_text(encoding="utf-8")
        for old, new in placeholders.items():
            text = text.replace(old, new)
        fp.write_text(text, encoding="utf-8")

    # =================================================================
    # === Optional git init
    # =================================================================
    if args.git:
        subprocess.run(["git", "init"], cwd=pr_root, check=True)
        subprocess.run(["git", "add", "."], cwd=pr_root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial scaffold from buildben"],
            cwd=pr_root,
            check=True,
        )

    # =================================================================
    # === Final message
    # =================================================================
    print(
        dedent(
            f"""
            ✅  {args.name} scaffold complete!

                cd "{pr_root}"
                direnv allow        # trust .envrc
                just venv-reset     # set up .venv via direnv
            
            Happy hacking 🎉
            """
        )
    )


