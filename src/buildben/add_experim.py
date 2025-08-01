#!/usr/bin/env python3
"""
buildben.init_experim – scaffold a new experiment folder.

Usage from CLI aggregator:
    buildben add-experim -n MY_TEST [--no-venv] [--no-freeze]
"""
from __future__ import annotations
import os
import argparse, datetime as dt, shutil, subprocess, sys
from pathlib import Path
from textwrap import dedent

from . import utils


# ================================================================== #
# === CLI wiring                                                     #
# ================================================================== #

CMD_NAME = "add-experim"  # < Name of the CLI-command
CMD_ALIASES = ["exp"] # < Alias shortcut of the CLI-command
DOC = f"Create a dated experiment scaffold inside ./experiments/. Aliases: {CMD_ALIASES}"

def _add_my_parser(subparsers: argparse._SubParsersAction) -> None:
    p: argparse.ArgumentParser = subparsers.add_parser(
        name=CMD_NAME,  # < the command name typed on the shell
        aliases=CMD_ALIASES,
        help=DOC,
        description=DOC,
    )
    p.add_argument(
        "name",
        nargs="?",
        default="",
        help="Experiment Name (e.g. validation, benchmark, etc.)",
    )
    p.add_argument("--no-venv", action="store_true", help="Skip venv creation")
    p.add_argument(
        "--no-freeze", action="store_true", help="Skip pip-compile lock"
    )
    # > Entrypoint, retrieved as args.func in cli.py
    p.set_defaults(func=_run) 


# ================================================================== #
# === implementation                                                 #
# ================================================================== #
def _run(args: argparse.Namespace) -> None:

    # === Retrieve Variables ==========================================
    PR_ROOT: Path = utils.find_project_root()
    PR_NAME = os.getenv("PROJECT_NAME")

    ### Experiment directory
    TODAY = dt.date.today().isoformat()
    EXP_NAME_FULL = f"{TODAY}_{args.name}"
    EXP_ROOT = PR_ROOT / "experiments" / EXP_NAME_FULL
    utils.warn_dir_overwrite(EXP_ROOT)

    # =================================================================
    # === Directory tree
    # =================================================================

    directories: list[Path] = [
        # EXP_ROOT / "env", # ?? This would complicate .dockerignore logic
        PR_ROOT / "experiments" / "resources", # < Potential use for experiments, must be manually copied into input!
        EXP_ROOT / "input",
        EXP_ROOT / "interm-output",
        EXP_ROOT / "output",
        EXP_ROOT / "scripts",
    ]
    for dir in directories:
        dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # === Copy template files
    # =================================================================

    # > {<_template_filename>: <destination_filepath>}
    # fmt: off
    transfers: dict[str, Path] = {
        "_REPORT.md": EXP_ROOT / "REPORT.md",
        "_run.py": EXP_ROOT / "run.py",
        "_paths.env": EXP_ROOT / ".paths.env",
        "_scripts_exp.py": EXP_ROOT / "scripts" / "exp.py",
        "_scripts_eval.py": EXP_ROOT / "scripts" / "eval.py",
    }
    # fmt: on

    tmpl_dir = Path(__file__).resolve().parent / "_templates_experim"
    utils.copy_templates(transfers=transfers, tmpl_dir=tmpl_dir)

    # =================================================================
    # === Placeholder substitution (same style as init_proj)
    # =================================================================

    placeholders = {
        "<experiment_name>": args.name,
        "{experiment_name}": args.name,
        "<experiment_name_full>": EXP_NAME_FULL,
        "{experiment_name_full}": EXP_NAME_FULL,
        "<bb_today>": TODAY,  # < bb_ makes it more unique to buildben
        "{bb_today}": TODAY,
        "<my_project>": PR_NAME,
        "{my_project}": PR_NAME,
    }

    utils.substitute_placeholders(
        filepaths=list(transfers.values()), placeholders=placeholders
    )
