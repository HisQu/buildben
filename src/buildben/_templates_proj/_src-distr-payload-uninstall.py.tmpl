"""Route removal through the authored procedure and independent saved controller."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

from apprc.definition.installation import InstallationError
from apprc.distribution.runtime import parse_uninstall_handoff_args
from apprc.distribution.runtime.controllers import (
    prepare_uninstall,
    start_uninstall_handoff,
)


def main(argv: list[str] | None = None) -> NoReturn:
    """Revalidate an accepted preview and hand off after the real caller exits."""
    original_pid, expected_revision, forwarded = parse_uninstall_handoff_args(
        argv
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--complete", action="store_true")
    parser.add_argument(
        "--category",
        action="append",
        choices=("config", "appdata", "cache", "state"),
    )
    parser.add_argument("--forget-retained", action="store_true")
    parser.add_argument("--yes", action="store_true")
    arguments = parser.parse_args(forwarded)
    if arguments.forget_retained and not arguments.complete:
        parser.error("--forget-retained requires --complete")
    preparation = prepare_uninstall(
        arguments.directory,
        categories=frozenset(arguments.category or ()),
        complete=arguments.complete,
        forget_retained=arguments.forget_retained,
    )
    if not preparation.can_execute or preparation.plan is None:
        details = "; ".join(item.message for item in preparation.diagnostics)
        raise InstallationError(
            details or "Installation cannot be removed safely."
        )
    if (
        expected_revision is not None
        and preparation.plan.expected_revision != expected_revision
    ):
        raise InstallationError("Installation changed after uninstall preview.")
    if expected_revision is None and not arguments.yes:
        if (
            not sys.stdin.isatty()
            or input("Remove the installed program? [y/N] ").casefold() != "y"
        ):
            raise SystemExit("Uninstall cancelled.")
    handoff = start_uninstall_handoff(
        preparation.plan,
        original_pid=original_pid or os.getpid(),
    )
    handoff.wait_ready()
    handoff.signal_exit()
    raise SystemExit(0)


if __name__ == "__main__":
    main()
