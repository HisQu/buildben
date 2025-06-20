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

CMD_NAME = "init-data"  # < Name of the CLI-command
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