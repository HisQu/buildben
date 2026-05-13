"""Small data objects used to describe Graphviz diagram content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from _shared.graphviz.theme import NODE_BORDER, RECT_FILL


# ===============================================================
# == Data Models
# ===============================================================

ClassifierKind = Literal["actor", "class", "interface"]


@dataclass(frozen=True)
class ClassifierNode:
    """Describe one UML-like classifier rendered as an HTML table.

    :param title: Main bold label shown in the node header.
    :param stereotype: Classifier label shown above the title.
    :param members: Body rows shown below the header.
    :param kind: Icon color family for the classifier.
    :param border_color: Border color used for the table cells.
    :param border_width: ``0`` for a borderless file/config look.
    :param title_italic: Whether to italicize the title.
    """

    title: str
    stereotype: str
    members: tuple[str, ...] = ()
    kind: ClassifierKind = "class"
    border_color: str = NODE_BORDER
    border_width: int = 1
    title_italic: bool = False


@dataclass(frozen=True)
class TextBox:
    """Describe one rounded gray text block.

    :param title: Bold heading shown first.
    :param rows: Plain rows rendered below the heading.
    :param fill: Background color of the block.
    :param monospace: Whether row text should use a monospace font.
    """

    title: str
    rows: tuple[str, ...]
    fill: str = RECT_FILL
    monospace: bool = False
