"""Minimal module entry point for <my_project>."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Create the starter CLI parser for the scaffolded project."""
    return argparse.ArgumentParser(
        prog="<my_project>",
        description="Starter entry point for the scaffolded project.",
    )


def main() -> None:
    """Parse CLI arguments for the scaffolded project entry point."""
    build_parser().parse_args()


if __name__ == "__main__":
    main()
