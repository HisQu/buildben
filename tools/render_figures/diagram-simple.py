"""Render the simplified dependency-management Graphviz figure."""

from __future__ import annotations

from graphviz import Digraph

from _shared.graphviz import (
    BLACK,
    BLUE,
    BLUE_FILL,
    ClassifierNode,
    GREEN,
    GREEN_FILL,
    NODE_BORDER,
    OLIVE,
    OLIVE_FILL,
    RED,
    add_classifier_node,
    add_package,
    connect,
    create_graph,
    invisible_edge,
    render_figure,
)


# ===============================================================
# == Figure Build
# ===============================================================


def build_diagram_simple() -> Digraph:
    """Build the simplified dependency-management diagram.

    :return: Configured Graphviz diagram.
    """

    graph = create_graph("diagram_simple_graphviz")
    graph.attr(nodesep="0.7", ranksep="1.05")

    ge = add_package(
        "GE",
        "Operating System",
        "Global Environment",
        OLIVE,
        OLIVE_FILL,
    )
    add_classifier_node(
        ge,
        "UV",
        ClassifierNode(
            "uv",
            "CLI",
            ("python install()", "venv()", "lock()", "sync()", "run()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )

    pdir = add_package("PDIR", "Project Directory", "Directory", BLUE, BLUE_FILL)
    add_classifier_node(
        pdir,
        "APP",
        ClassifierNode("main.py\n(or other code)", "File", (), "class", BLACK, 0),
    )
    add_classifier_node(
        pdir,
        "PPRT",
        ClassifierNode(
            "pyproject.toml",
            "Config",
            ("Dependencies", "Project Metadata"),
            "class",
            BLACK,
            0,
        ),
    )
    add_classifier_node(
        pdir,
        "LOCK",
        ClassifierNode(
            "uv.lock",
            "Lock-File",
            ("Dependencies", "Versions", "Sources"),
            "class",
            BLACK,
            0,
        ),
    )

    add_classifier_node(
        graph,
        "USER",
        ClassifierNode(
            "User",
            "Actor",
            ("eat()", "sleep()", "code()"),
            "actor",
            NODE_BORDER,
            1,
            True,
        ),
    )

    venv = add_package("VENV", ".venv", "Virtual Environment", GREEN, GREEN_FILL)
    add_classifier_node(
        venv,
        "PKG",
        ClassifierNode("Python Dependencies", "Pkg", (), "class", BLACK, 0),
    )
    graph.subgraph(ge)
    graph.subgraph(pdir)
    graph.subgraph(venv)

    invisible_edge(graph, "UV", "PPRT")
    invisible_edge(graph, "PPRT", "USER")
    invisible_edge(graph, "USER", "PKG")

    connect(graph, "USER", "PPRT", "edits", BLUE, constraint=False)
    connect(graph, "UV", "LOCK", "resolves", BLUE, constraint=False)
    connect(graph, "USER", "LOCK", "reviews", BLUE, constraint=False)

    connect(
        graph,
        "UV",
        "PKG",
        ("creates .venv", "& syncs"),
        GREEN,
        bold=True,
        penwidth="4",
        constraint=False,
    )
    connect(
        graph,
        "USER",
        "PKG",
        ("runs uv,", "activates", "& manages"),
        GREEN,
        constraint=False,
    )

    connect(graph, "APP", "PKG", "requires", RED, dashed=True, constraint=False)
    connect(graph, "UV", "PPRT", "requires", RED, dashed=True, constraint=False)
    connect(graph, "UV", "LOCK", "reads", RED, dashed=True, constraint=False)

    return graph


# ===============================================================
# == Entrypoint
# ===============================================================


def main() -> None:
    """Render the simplified dependency-management figure.

    :return: ``None``. The output files are written below ``assets/figures``.
    """

    render_figure(build_diagram_simple(), "diagram-simple")


if __name__ == "__main__":
    main()
