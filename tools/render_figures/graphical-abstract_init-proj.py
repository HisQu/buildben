"""Render the ``bube init-proj`` graphical abstract with Graphviz."""

from __future__ import annotations

from graphviz import Digraph

from _shared.graphviz import (
    BLUE,
    BLUE_FILL,
    OLIVE,
    OLIVE_FILL,
    RECT_FILL,
    RED,
    STANDARDS_FILL,
    TextBox,
    add_package,
    add_text_box,
    connect,
    create_graph,
    render_figure,
)


# ===============================================================
# == Figure Build
# ===============================================================


def build_graphical_abstract_init_proj() -> Digraph:
    """Build the graphical abstract for ``bube init-proj``.

    :return: Configured Graphviz diagram.
    """

    graph = create_graph("graphical_abstract_init_proj_graphviz")
    graph.attr(nodesep="0.85", ranksep="1.0")

    buildben = add_package("BB", "buildben", "Python Package", OLIVE, OLIVE_FILL)
    add_text_box(
        buildben,
        "TEMP",
        TextBox(
            "Templates:",
            (
                "&#8226; pyproject.toml",
                "&#8226; .envrc",
                "&#8226; justfile",
                "&#8226; ...",
            ),
            RECT_FILL,
            True,
        ),
    )
    add_text_box(
        buildben,
        "BBinitcli",
        TextBox("$ bube init-proj", (), RECT_FILL, True),
    )

    project = add_package(
        "P",
        "Project",
        "Directory & Environment",
        BLUE,
        BLUE_FILL,
    )
    add_text_box(
        project,
        "Tools",
        TextBox(
            "Universal Tools:",
            ("&#8226; direnv", "&#8226; just", "&#8226; ..."),
            RECT_FILL,
            True,
        ),
    )
    add_text_box(
        project,
        "PyTools",
        TextBox(
            "Python Tools:",
            ("&#8226; uv sync", "&#8226; uv.lock", "&#8226; .venv", "&#8226; ..."),
            RECT_FILL,
            True,
        ),
    )

    add_text_box(
        graph,
        "Standards",
        TextBox(
            "Python Standards:",
            (
                "&#8226; PEP 405: Virtual-environment",
                "&#8226; PEP 621: pyproject.toml",
                "&#8226; PEP 660: Editable install",
                "&#8226; PEP 751: Lock-files",
                "&#8226; uv: uv.lock workflow",
                "&#8226; PyPA: src/-Layout",
            ),
            STANDARDS_FILL,
            True,
        ),
    )
    graph.subgraph(buildben)
    graph.subgraph(project)

    connect(graph, "TEMP", "BBinitcli", "copied by", OLIVE)
    connect(
        graph,
        "BBinitcli",
        "Tools",
        "creates project scaffold (buildben is no dependency of project)",
        BLUE,
        bold=True,
        penwidth="4",
    )
    connect(graph, "Tools", "PyTools", ("automate", "& simplify"), BLUE, bold=True)
    connect(
        graph,
        "PyTools",
        "Standards",
        "comply with",
        RED,
        bold=True,
        dashed=True,
        constraint=False,
    )
    connect(
        graph,
        "TEMP",
        "Standards",
        "comply with",
        RED,
        bold=True,
        dashed=True,
        constraint=False,
    )

    return graph


# ===============================================================
# == Entrypoint
# ===============================================================


def main() -> None:
    """Render the ``bube init-proj`` graphical abstract.

    :return: ``None``. The output files are written below ``assets/figures``.
    """

    render_figure(build_graphical_abstract_init_proj(), "graphical-abstract_init-proj")


if __name__ == "__main__":
    main()
