"""Reusable drawing helpers for Graphviz figure construction."""

from __future__ import annotations

from collections.abc import Iterable

from graphviz import Digraph

from graphviz_support.labels import classifier_label, edge_label, text_box_label
from graphviz_support.models import ClassifierNode, TextBox
from graphviz_support.theme import BLACK, FONT, FONT_SIZE


# ===============================================================
# == Graph Setup
# ===============================================================


def create_graph(name: str, *, rankdir: str = "LR") -> Digraph:
    """Create a diagram with shared Graphviz defaults.

    :param name: Graph identifier used in the DOT source.
    :param rankdir: Main layout direction.
    :return: A configured :class:`graphviz.Digraph`.
    """

    graph = Digraph(name=name, engine="dot")
    graph.attr(
        bgcolor="transparent",
        compound="true",
        fontname=FONT,
        fontsize=FONT_SIZE,
        margin="0.04",
        nodesep="0.75",
        outputorder="edgesfirst",
        pad="0.04",
        rankdir=rankdir,
        ranksep="1.15",
        splines="true",
    )
    graph.attr("node", fontname=FONT, fontsize=FONT_SIZE, shape="plain")
    graph.attr(
        "edge",
        arrowsize="0.9",
        fontcolor=BLACK,
        fontname=FONT,
        fontsize=FONT_SIZE,
        penwidth="2.5",
    )
    return graph


# ===============================================================
# == Packages And Nodes
# ===============================================================


def add_package(
    name: str,
    label: str,
    stereotype: str,
    color: str,
    fill: str,
) -> Digraph:
    """Create a rounded Graphviz cluster used as a package substitute.

    :param name: Cluster identifier without the ``cluster_`` prefix.
    :param label: Visible group title.
    :param stereotype: Secondary label shown below the title.
    :param color: Border and font color.
    :param fill: Translucent package fill color.
    :return: The mutable cluster graph.
    """

    cluster = Digraph(name=f"cluster_{name}")
    cluster.attr(
        color=color,
        fillcolor=fill,
        fontcolor=color,
        fontname=FONT,
        fontsize=FONT_SIZE,
        label=package_label(label, stereotype),
        labelloc="t",
        margin="18",
        penwidth="2",
        style="rounded,filled",
    )
    cluster.attr("node", fontname=FONT, fontsize=FONT_SIZE, shape="plain")
    return cluster


def package_label(label: str, stereotype: str) -> str:
    """Build the two-line label used by package clusters.

    :param label: Visible group title.
    :param stereotype: Secondary classifier text.
    :return: Escaped Graphviz label text.
    """

    return f"{label}\n<<{stereotype}>>"


def add_classifier_node(graph: Digraph, node_id: str, spec: ClassifierNode) -> None:
    """Add one classifier node to a graph.

    :param graph: Target graph or cluster.
    :param node_id: DOT identifier.
    :param spec: Node content and style.
    :return: ``None``.
    """

    graph.node(node_id, label=classifier_label(spec))


def add_text_box(graph: Digraph, node_id: str, spec: TextBox) -> None:
    """Add one rounded multi-line text box.

    :param graph: Target graph or cluster.
    :param node_id: DOT identifier.
    :param spec: Text content and visual style.
    :return: ``None``.
    """

    graph.node(node_id, label=text_box_label(spec))


# ===============================================================
# == Edges
# ===============================================================


def connect(
    graph: Digraph,
    tail: str,
    head: str,
    label: str | Iterable[str],
    color: str,
    *,
    bold: bool = False,
    dashed: bool = False,
    penwidth: str = "2.5",
    constraint: bool = True,
    weight: str | None = None,
) -> None:
    """Add a semantic edge with the shared figure styling.

    :param graph: Target graph.
    :param tail: Source node identifier.
    :param head: Target node identifier.
    :param label: Edge label text.
    :param color: Stroke and label color.
    :param bold: Whether to bold the label.
    :param dashed: Whether to use a dash pattern.
    :param penwidth: Edge stroke width.
    :param constraint: Whether the edge constrains DOT ranking.
    :param weight: Optional DOT edge weight.
    :return: ``None``.
    """

    attrs = {
        "color": color,
        "fontcolor": color,
        "label": edge_label(label, bold=bold),
        "penwidth": penwidth,
        "style": "dashed" if dashed else "solid",
    }
    if not constraint:
        attrs["constraint"] = "false"
    if weight is not None:
        attrs["weight"] = weight
    graph.edge(tail, head, **attrs)


def invisible_edge(graph: Digraph, tail: str, head: str, *, weight: str = "10") -> None:
    """Add a hidden edge that nudges DOT rank order.

    :param graph: Target graph.
    :param tail: Source node identifier.
    :param head: Target node identifier.
    :param weight: DOT layout weight.
    :return: ``None``.
    """

    graph.edge(tail, head, style="invis", weight=weight)
