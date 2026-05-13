"""Rendering helpers for Graphviz figure scripts."""

from __future__ import annotations

from pathlib import Path

from graphviz import Digraph


# ===============================================================
# == Paths
# ===============================================================

FIGURES_DIR = Path(__file__).resolve().parents[1]
GRAPHVIZ_SUFFIX = "graphviz"


# ===============================================================
# == Rendering
# ===============================================================


def render_figure(
    graph: Digraph,
    figure_name: str,
    *,
    output_suffix: str = GRAPHVIZ_SUFFIX,
) -> None:
    """Render one graph as SVG and PNG.

    :param graph: Diagram to render.
    :param figure_name: Figure directory and base filename.
    :param output_suffix: Suffix appended to the output filename.
    :return: ``None``. Graphviz writes the files.
    """

    output_dir = FIGURES_DIR / figure_name
    output_name = f"{figure_name}-{output_suffix}"
    output_dir.mkdir(parents=True, exist_ok=True)
    graph.render(
        directory=output_dir,
        filename=output_name,
        format="svg",
        cleanup=True,
    )
    graph.render(
        directory=output_dir,
        filename=output_name,
        format="png",
        cleanup=True,
    )
