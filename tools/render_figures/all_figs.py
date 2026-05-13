"""Render every Graphviz figure asset for this repository."""

from __future__ import annotations

from pathlib import Path
from runpy import run_path


# ===============================================================
# == Paths
# ===============================================================

SCRIPTS_DIR = Path(__file__).resolve().parent
FIGURE_SCRIPTS = (
    "diagram.py",
    "diagram-simple.py",
    "graphical-abstract_init-proj.py",
)


# ===============================================================
# == Entrypoint
# ===============================================================


def main() -> None:
    """Render all repository figure assets.

    :return: ``None``. Each child script writes one SVG and one PNG.
    """

    for script_name in FIGURE_SCRIPTS:
        run_path(str(SCRIPTS_DIR / script_name), run_name="__main__")


if __name__ == "__main__":
    main()
