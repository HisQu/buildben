"""Render the full buildben dependency-management Graphviz figure."""

from __future__ import annotations

from graphviz import Digraph

from graphviz_support import (
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


def build_diagram() -> Digraph:
    """Build the full dependency-management diagram.

    :return: Configured Graphviz diagram.
    """

    graph = create_graph("diagram_graphviz")
    graph.attr(nodesep="0.55", ranksep="0.85", splines="polyline")

    ge = add_package(
        "GE",
        "Operating System",
        "Global Environment",
        OLIVE,
        OLIVE_FILL,
    )
    add_classifier_node(
        ge,
        "UVG",
        ClassifierNode(
            "uv",
            "CLI",
            ("tool install()", "tool run()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )
    add_classifier_node(
        ge,
        "B",
        ClassifierNode(
            "buildben",
            "CLI",
            ("init-proj()", "add-experiment()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )
    add_classifier_node(
        ge,
        "D",
        ClassifierNode(
            "Direnv",
            "CLI",
            ("layout()", "direnv reload()", "direnv exec()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )
    add_classifier_node(
        ge,
        "J",
        ClassifierNode("just", "CLI", (), "interface", BLACK, 1, True),
    )

    pdir = add_package("PDIR", "Project Directory", "Directory", BLUE, BLUE_FILL)
    add_classifier_node(
        pdir,
        "PPRT",
        ClassifierNode(
            "pyproject.toml",
            "Config",
            ("Dependencies", "Setup Configuration"),
            "class",
            BLACK,
            0,
        ),
    )
    add_classifier_node(
        pdir,
        "LOCK",
        ClassifierNode(
            "uv.lock\npylock.toml",
            "Lock-Files",
            ("Dependencies", "Versions & Sources"),
            "class",
            BLACK,
            0,
        ),
    )
    add_classifier_node(
        pdir,
        "ERC",
        ClassifierNode(
            ".envrc", "Config", ("PROJECT_NAME", "ENV_VARS"), "class", BLACK, 0
        ),
    )
    add_classifier_node(
        pdir,
        "JF",
        ClassifierNode(
            "justfile", "Recipes", ("reset()", "install-deps()", "...()"), "class"
        ),
    )

    venv = add_package("VENV", ".venv", "Virtual Environment", GREEN, GREEN_FILL)
    add_classifier_node(
        venv,
        "UVV",
        ClassifierNode(
            "uv",
            "Tool",
            ("venv()", "lock()", "sync()", "run()"),
            "interface",
            NODE_BORDER,
            1,
            True,
        ),
    )
    add_classifier_node(
        venv,
        "PD",
        ClassifierNode("python dependencies", "Pkg", (), "class", BLACK, 0),
    )
    graph.subgraph(ge)
    graph.subgraph(pdir)
    graph.subgraph(venv)

    invisible_edge(graph, "UVG", "B")
    invisible_edge(graph, "B", "PPRT")
    invisible_edge(graph, "PPRT", "UVV")
    invisible_edge(graph, "UVV", "PD")

    connect(graph, "UVG", "B", ("installs", "as tool"), OLIVE)
    connect(
        graph,
        "B",
        "PPRT",
        ("copies", "templates", "(cookiecutter)"),
        BLUE,
        bold=True,
        penwidth="4",
    )
    connect(graph, "UVV", "LOCK", ("resolves", "& exports"), BLUE)
    connect(graph, "UVV", "PPRT", "editable install", BLUE, constraint=False)

    connect(
        graph,
        "UVG",
        "UVV",
        ("creates", ".venv"),
        GREEN,
        bold=True,
        penwidth="4",
    )
    connect(graph, "UVV", "PD", "syncs", GREEN)
    connect(graph, "ERC", "UVV", "activates", GREEN, constraint=False)
    connect(graph, "JF", "UVV", "runs", GREEN)

    connect(graph, "ERC", "D", "requires", RED, dashed=True)
    connect(graph, "JF", "J", "requires", RED, dashed=True)
    connect(graph, "JF", "D", "requires", RED, dashed=True)
    connect(graph, "UVV", "PPRT", "reads dependency specs", RED, dashed=True)

    return graph


# ===============================================================
# == Entrypoint
# ===============================================================


def main() -> None:
    """Render the full dependency-management figure.

    :return: ``None``. The output files are written below ``assets/figures``.
    """

    render_figure(build_diagram(), "diagram")


if __name__ == "__main__":
    main()
