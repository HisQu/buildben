"""Inject one filesystem interruption while executing the real standalone installer."""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    """Fail a selected migration boundary once without replacing lifecycle logic."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boundary", choices=("retire", "promote", "receipt"), required=True
    )
    parser.add_argument("installer", type=Path)
    arguments, forwarded = parser.parse_known_args()
    rename = Path.rename
    unlink = Path.unlink
    interrupted = False

    def fail_once(path: Path, *, rename_operation: bool) -> None:
        nonlocal interrupted
        selected = (
            (
                arguments.boundary == "retire"
                and rename_operation
                and path.name == "lifecycle.py"
            )
            or (
                arguments.boundary == "promote"
                and rename_operation
                and "migration-staged" in path.parts
            )
            or (
                arguments.boundary == "receipt"
                and not rename_operation
                and path.name == "receipt.json"
            )
        )
        if selected and not interrupted:
            interrupted = True
            raise OSError(f"Maintained fixture interruption at {arguments.boundary}")

    def interrupted_rename(self: Path, target: str | os.PathLike[str]) -> Path:
        fail_once(self, rename_operation=True)
        return rename(self, target)

    def interrupted_unlink(self: Path, missing_ok: bool = False) -> None:
        fail_once(self, rename_operation=False)
        unlink(self, missing_ok=missing_ok)

    Path.rename = interrupted_rename
    Path.unlink = interrupted_unlink
    sys.argv = [str(arguments.installer), *forwarded]
    try:
        runpy.run_path(str(arguments.installer), run_name="__main__")
    finally:
        Path.rename = rename
        Path.unlink = unlink


if __name__ == "__main__":
    main()
