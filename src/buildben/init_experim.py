#!/usr/bin/env python3
"""
buildben.init_experim – scaffold a new experiment folder.

Usage from CLI aggregator:
    buildben init-experim -n MY_TEST [--no-venv] [--no-freeze]
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
def add_parser(subparsers: argparse._SubParsersAction) -> None:
    DOC = "Create a dated experiment scaffold inside ./experiments/"
    p: argparse.ArgumentParser = subparsers.add_parser(
        "init-experim",  # < the command name typed on the shell
        help=DOC,
        description=DOC,
    )
    p.add_argument("-n", "--name", default="", help="Experiment Name (e.g. validation, benchmark, etc.)")
    p.add_argument("--no-venv", action="store_true", help="Skip venv creation")
    p.add_argument(
        "--no-freeze", action="store_true", help="Skip pip-compile lock"
    )
    p.set_defaults(func=_run)


# ================================================================== #
# === implementation                                                 #
# ================================================================== #
def _run(args: argparse.Namespace) -> None:

    ### Locate project root:
    PR_ROOT = utils.detect_root()

    ### Experiment directory
    today = dt.date.today().isoformat()
    EXP_ROOT = PR_ROOT / "experiments" / f"{today}_{args.name}"
    utils.warn_dir_overwrite(EXP_ROOT)

    # =================================================================
    # === Directory tree
    # =================================================================

    directories: list[Path] = [
        EXP_ROOT / "env",
        EXP_ROOT / "data",
        EXP_ROOT / "scripts",
        EXP_ROOT / "output",
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
        "<bb_date>": today,  # < bb_ makes it more unique to buildben
        "{bb_date}": today,
        "<my_project>": os.getenv("PROJECT_NAME"),
        "{my_project}": os.getenv("PROJECT_NAME"),
    }

    utils.substitute_placeholders(
        filepaths=list(transfers.values()), placeholders=placeholders
    )
    
    # =================================================================
    # === Optional .venv + dependency freeze 
    # =================================================================

#     if not args.no_freeze:
#         _freeze_reqs(EXP_ROOT)
#     if not args.no_venv:
#         _create_venv(EXP_ROOT)

#     print(
#         dedent(
#             f"""
#         ✅  experiment created at  {EXP_ROOT}
#             cd experiments/{today}_{args.name}
#             direnv allow          # trust .envrc
#             just install          # compile & install deps (optionally)
#     """
#         )
#     )


# # ================================================================== #
# # === helpers                                                        #
# # ================================================================== #
# def _freeze_reqs(root: Path) -> None:
#     req_in = root / "env" / "requirements.in"
#     req_out = root / "env" / "requirements.txt"
#     pip_compile = shutil.which("pip-compile")
#     if pip_compile is None:
#         print("∙ Skipping freeze (pip-compile not on PATH)")
#         return
#     subprocess.run([pip_compile, req_in, "-o", req_out], check=True)
#     print("✓  requirements.txt frozen")


# def _create_venv(root: Path) -> None:
#     import venv, sys as _sys

#     print("⏳  creating .venv …")
#     venv.EnvBuilder(with_pip=True).create(root / ".venv")
#     pip = root / ".venv" / "bin" / "pip"
#     subprocess.run(
#         [pip, "install", "-r", root / "env/requirements.in"], check=False
#     )
#     print(
#         "✓  .venv ready (activate with 'direnv reload' or '. .venv/bin/activate')"
#     )


# # ================================================================== #
# def main() -> None:
#     # standalone usage: fall back to simple parser
#     pr = argparse.ArgumentParser()
#     pr.add_argument("-n", "--name", required=True)
#     pr.add_argument("--no-venv", action="store_true")
#     pr.add_argument("--no-freeze", action="store_true")
#     ns = pr.parse_args()
#     _run(ns)


# if __name__ == "__main__":
#     main()
