"""Update or check Mermaid templates copied into new Buildben projects."""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, cast

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "src" / "buildben" / "_templates_proj"
TEMPLATE_FILES = {
    "flowchart": "_assets-flowchart.IGNORE.mmd",
    "class-diagram": "_assets-classdiagram.IGNORE.mmd",
}


class _GraphigsMermaid(Protocol):
    """Describe the one Graphigs function used by this maintenance command."""

    template_source: Callable[[str], str]


def _graphigs_template_source() -> Callable[[str], str]:
    """Load the canonical Mermaid source from the separately installed Graphigs.

    :return: Graphigs function that retrieves a named Mermaid template.
    :raises RuntimeError: If Graphigs is unavailable in the maintainer environment.
    """
    try:
        mermaid = cast(_GraphigsMermaid, importlib.import_module("graphigs.mermaid"))
    except ImportError as exc:
        raise RuntimeError(
            "Graphigs is required to sync Mermaid templates. Install the Graphigs "
            "checkout in this environment first."
        ) from exc
    # > This import stays optional so Buildben's runtime has no Graphigs dependency.
    return mermaid.template_source


def sync_templates(
    template_source: Callable[[str], str],
    template_dir: Path,
    *,
    check: bool = False,
) -> int:
    """Compare or copy canonical Graphigs templates into Buildben's scaffold.

    :param template_source: Graphigs function that returns source for a template kind.
    :param template_dir: Directory containing Buildben's scaffold snapshots.
    :param check: Compare files without writing when true.
    :return: Zero when the snapshots match or were updated, one when check finds drift.
    """
    expected = {
        filename: f"{template_source(kind).rstrip()}\n"
        for kind, filename in TEMPLATE_FILES.items()
    }
    stale = [
        filename
        for filename, source in expected.items()
        if not (template_dir / filename).is_file()
        or (template_dir / filename).read_text(encoding="utf-8") != source
    ]

    if check:
        if stale:
            for filename in stale:
                print(f"Out of date: {template_dir / filename}", file=sys.stderr)
            return 1
        print("Mermaid scaffold templates are up to date.")
        return 0

    template_dir.mkdir(parents=True, exist_ok=True)
    for filename, source in expected.items():
        (template_dir / filename).write_text(source, encoding="utf-8")
        print(f"Updated: {template_dir / filename}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse arguments for the maintainer-only sync command.

    :param argv: Optional argument vector used by tests.
    :return: Parsed command options.
    """
    parser = argparse.ArgumentParser(
        description="Update Buildben's Mermaid scaffold snapshots from Graphigs."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale snapshots without changing files.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Graphigs-to-Buildben Mermaid template sync.

    :param argv: Optional argument vector used by tests.
    :return: Process exit code.
    """
    args = parse_args(argv)
    try:
        template_source = _graphigs_template_source()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return sync_templates(template_source, TEMPLATE_DIR, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
