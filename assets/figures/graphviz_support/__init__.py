"""Shared helpers for repository-local Graphviz figure scripts."""

from graphviz_support.drawing import (
    add_classifier_node,
    add_package,
    add_text_box,
    connect,
    create_graph,
    invisible_edge,
)
from graphviz_support.models import ClassifierNode, TextBox
from graphviz_support.rendering import render_figure
from graphviz_support.theme import (
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
