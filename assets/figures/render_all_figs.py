"""Render every Graphviz figure asset for this repository."""

from __future__ import annotations

from render_diagram import main as render_diagram
from render_diagram_simple import main as render_diagram_simple
from render_graphical_abstract_init_proj import (
    main as render_graphical_abstract_init_proj,
)


# ===============================================================
# == Entrypoint
# ===============================================================


def main() -> None:
    """Render all repository figure assets.

    :return: ``None``. Each child script writes one SVG and one PNG.
    """

    render_diagram()
    render_diagram_simple()
    render_graphical_abstract_init_proj()


if __name__ == "__main__":
    main()
