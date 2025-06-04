#!/usr/bin/env python3
"""Scaffold a new src-layout Python project.

Usage:
    init_project.py -n <project_name> [-t <target_dir>] [-g]

Options:
    -n   Name of the project (required, must be valid import name)
    -t   Target directory to create the new project in. [default: .]
    -g   Initialise a git repository and create the first commit.
"""

from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def main():
    # =================================================================
    # === CLI parsing
    # =================================================================
    parser = argparse.ArgumentParser(description="Scaffold a Python project")
    parser.add_argument("-n", "--name", required=True, help="project name")
    parser.add_argument(
        "-t",
        "--target-dir",
        default=".",
        help="directory in which to create project",
    )
    parser.add_argument(
        "-g", "--git", action="store_true", help="initialise git repo"
    )
    parser.add_argument(
        "-u",
        "--github-username",
        default="github-username",
        help="Github Username",
    )
    args: argparse.Namespace = parser.parse_args()

    ### Validate project name
    IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    if not IDENT_RE.match(args.name):
        sys.exit("💥  Project name must be a valid Python identifier")

    ### Resolve path to project root
    proj_root: Path = Path(args.target_dir).expanduser().resolve() / args.name
    # > Warn user if project root already exists
    if proj_root.exists():
        answer = input(
            f"⚠️  {proj_root} exists and files may be overwritten. Continue? [y/N] "
        ).lower()
        if answer not in {"y", "yes"}:
            sys.exit("Aborted by user")

    # =================================================================
    # === Directory tree
    # =================================================================

    directories: list[Path] = [
        proj_root / "tests",
        proj_root / "assets",
        proj_root / "examples",
        proj_root / "experiments",
        proj_root / ".github" / "workflows",
        proj_root / ".github" / "workflows_inactive",
        proj_root / "src" / args.name,
        proj_root / "src" / args.name / "data",
        proj_root / "src" / args.name / "images",
    ]
    for dir in directories:
        dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # === Copy template files
    # =================================================================
    script_dir = Path(__file__).resolve().parent
    tmpl_dir = script_dir / "templates"

    # > {<_template_filename>: <destination_filepath>}
    copies: dict[str, Path] = {
        "_README.md": proj_root / "README.md",
        "_gitignore": proj_root / ".gitignore",
        "_pyproject.toml": proj_root / "pyproject.toml",
        "_envrc": proj_root / ".envrc",
        "_justfile": proj_root / "justfile",
        "_flowchart.mmd": proj_root / "assets" / "flowchart.mmd",
        "_classdiagram.mmd": proj_root / "assets" / "classdiagram.mmd",
        "_codecov.yml": proj_root
        / ".github"
        / "workflows_inactive"
        / "codecov.yml",
    }

    for tmpl_fn, dst_fp in copies.items():
        tmpl_fp = tmpl_dir / tmpl_fn
        shutil.copy2(tmpl_fp, dst_fp, follow_symlinks=False)

    # =================================================================
    # === Placeholder substitution
    # =================================================================
    placeholders = {
        "<my_project>": args.name,
        "{my_project}": args.name,
        "<github_username>": args.github_username,
        "{github_username}": args.github_username,
    }

    ### Specify files to edit (or just gather them all)
    copies_edit: list[Path] = list(copies.values())
    # copies_edit: list[Path] = [
    #     proj_root / "README.md",
    #     proj_root / ".envrc",
    #     proj_root / "justfile",
    # ]

    for fp in copies_edit:
        text = fp.read_text(encoding="utf-8")
        for old, new in placeholders.items():
            text = text.replace(old, new)
        fp.write_text(text, encoding="utf-8")

    # =================================================================
    # === Optional git init
    # =================================================================
    if args.git:
        subprocess.run(["git", "init"], cwd=proj_root, check=True)
        subprocess.run(["git", "add", "."], cwd=proj_root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial scaffold from buildben"],
            cwd=proj_root,
            check=True,
        )

    # =================================================================
    # === Final message
    # =================================================================
    print(
        dedent(
            f"""
            ✅  {args.name} scaffold complete!

                cd "{proj_root}"
                direnv allow        # trust .envrc
                just venv-reset     # set up .venv via direnv
            
            Happy hacking 🎉
            """
        )
    )


if __name__ == "__main__":
    main()
