"""Inject one filesystem interruption while executing the real standalone installer."""

from __future__ import annotations

import argparse
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Fail a selected migration boundary once without replacing lifecycle logic."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boundary",
        choices=(
            "retire",
            "promote",
            "receipt",
            "before-backend",
            "after-backend",
            "authority",
            "ready-order",
        ),
        required=True,
    )
    parser.add_argument("--legacy-root", type=Path)
    parser.add_argument("installer", type=Path)
    arguments, forwarded = parser.parse_known_args()
    run = subprocess.run
    replace = os.replace
    rename = Path.rename
    unlink = Path.unlink
    interrupted = False

    def interrupted_run(command, *args, **kwargs):
        nonlocal interrupted
        selected = (
            arguments.boundary in {"before-backend", "after-backend"}
            and isinstance(command, (list, tuple))
            and "tool" in command
            and "install" in command
        )
        if selected and not interrupted:
            if arguments.boundary == "before-backend":
                interrupted = True
                raise OSError("Maintained fixture interruption before backend")
            run(command, *args, **kwargs)
            interrupted = True
            raise OSError("Maintained fixture interruption after backend")
        return run(command, *args, **kwargs)

    def interrupted_replace(source, target, *args, **kwargs):
        nonlocal interrupted
        selected = (
            arguments.boundary in {"authority", "ready-order"}
            and Path(target).name == "installation.json"
        )
        if selected and arguments.boundary == "ready-order":
            record = json.loads(Path(source).read_text(encoding="utf-8"))
            if record["status"] == "ready":
                if arguments.legacy_root is None:
                    raise RuntimeError("--legacy-root is required for ready-order.")
                if any(
                    (arguments.legacy_root / name).exists()
                    for name in ("receipt.json", "lifecycle.py")
                ):
                    raise AssertionError(
                        "Legacy authority remained when ready was published."
                    )
        if selected and arguments.boundary == "authority" and not interrupted:
            replace(source, target, *args, **kwargs)
            interrupted = True
            raise OSError("Maintained fixture interruption after authority write")
        return replace(source, target, *args, **kwargs)

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
    subprocess.run = interrupted_run
    os.replace = interrupted_replace
    try:
        runpy.run_path(str(arguments.installer), run_name="__main__")
    finally:
        subprocess.run = run
        os.replace = replace
        Path.rename = rename
        Path.unlink = unlink


if __name__ == "__main__":
    main()
