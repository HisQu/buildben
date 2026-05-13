"""Shared helpers for repository-local Graphviz figure scripts."""

from _shared.graphviz.drawing import (
    add_classifier_node,
    add_package,
    add_text_box,
    connect,
    create_graph,
    invisible_edge,
)
from _shared.graphviz.models import ClassifierNode, TextBox
from _shared.graphviz.rendering import render_figure
from _shared.graphviz.theme import (
    BLACK,
    BLUE,
    BLUE_FILL,
    GREEN,
    GREEN_FILL,
    NODE_BORDER,
    OLIVE,
    OLIVE_FILL,
    RED,
    RECT_FILL,
    STANDARDS_FILL,
)

__all__ = [
    "BLACK",
    "BLUE",
    "BLUE_FILL",
    "ClassifierNode",
    "GREEN",
    "GREEN_FILL",
    "NODE_BORDER",
    "OLIVE",
    "OLIVE_FILL",
    "RECT_FILL",
    "RED",
    "STANDARDS_FILL",
    "TextBox",
    "add_classifier_node",
    "add_package",
    "add_text_box",
    "connect",
    "create_graph",
    "invisible_edge",
    "render_figure",
]
