#!/usr/bin/env python3
"""
buildben.init_experim – scaffold a new experiment folder.

Usage from CLI aggregator:
    buildben init-experim -n MY_TEST [--no-venv] [--no-freeze]
"""
from __future__ import annotations
import argparse, datetime as dt, shutil, subprocess, sys
from pathlib import Path
from textwrap import dedent


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
    p.add_argument("-n", "--name", required=True, help="experiment slug")
    p.add_argument("--no-venv", action="store_true", help="skip .venv creation")
    p.add_argument(
        "--no-freeze", action="store_true", help="skip pip-compile lock"
    )
    p.set_defaults(func=_run)


# ================================================================== #
# === implementation                                                 #
# ================================================================== #
def _run(args: argparse.Namespace) -> None:
    today = dt.date.today().isoformat()
    project_root = Path.cwd()  # assume user is already in the project
    exp_root = project_root / "experiments" / f"{today}_{args.name}"
    if exp_root.exists():
        sys.exit(f"✗ {exp_root} already exists — choose a different name")

    # === copy templates ==========================================
    tmpl_dir = Path(__file__).resolve().parent / "_templates_experim"
    shutil.copytree(
        tmpl_dir, exp_root, dirs_exist_ok=True, copy_function=shutil.copy2
    )
    print(f"✓  Templates copied from {tmpl_dir}")

    # === placeholder substitution (same style as init_proj) ============
    placeholders = {
        "<exp_name>": args.name,
        "{exp_name}": args.name,
        "<date>": today,
        "{date}": today,
    }
    for fp in exp_root.rglob("*"):
        if fp.is_file() and fp.suffix in {".md", ".py", ".sh"}:
            text = fp.read_text(encoding="utf-8")
            for old, new in placeholders.items():
                text = text.replace(old, new)
            fp.write_text(text, encoding="utf-8")

    # === optional .venv + dependency freeze =====================-
    if not args.no_freeze:
        _freeze_reqs(exp_root)
    if not args.no_venv:
        _create_venv(exp_root)

    print(
        dedent(
            f"""
        ✅  experiment created at  {exp_root}
            cd experiments/{today}_{args.name}
            direnv allow          # trust .envrc
            just install          # compile & install deps (optionally)
    """
        )
    )


# ================================================================== #
# helpers                                                            #
# ================================================================== #
def _freeze_reqs(root: Path) -> None:
    req_in = root / "env" / "requirements.in"
    req_out = root / "env" / "requirements.txt"
    pip_compile = shutil.which("pip-compile")
    if pip_compile is None:
        print("∙ Skipping freeze (pip-compile not on PATH)")
        return
    subprocess.run([pip_compile, req_in, "-o", req_out], check=True)
    print("✓  requirements.txt frozen")


def _create_venv(root: Path) -> None:
    import venv, sys as _sys

    print("⏳  creating .venv …")
    venv.EnvBuilder(with_pip=True).create(root / ".venv")
    pip = root / ".venv" / "bin" / "pip"
    subprocess.run(
        [pip, "install", "-r", root / "env/requirements.in"], check=False
    )
    print(
        "✓  .venv ready (activate with 'direnv reload' or '. .venv/bin/activate')"
    )


# ================================================================== #
def main() -> None:
    # standalone usage: fall back to simple parser
    pr = argparse.ArgumentParser()
    pr.add_argument("-n", "--name", required=True)
    pr.add_argument("--no-venv", action="store_true")
    pr.add_argument("--no-freeze", action="store_true")
    ns = pr.parse_args()
    _run(ns)


if __name__ == "__main__":
    main()
