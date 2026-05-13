"""Visual constants shared by Graphviz figure scripts.

The values in this module define the house style for the generated diagrams:
transparent backgrounds, bright translucent package regions, gray inner nodes,
and color-coded semantic arrows.
"""

from __future__ import annotations


# ===============================================================
# == Typography
# ===============================================================

FONT = "sans-serif"
MONO_FONT = "monospace"
FONT_SIZE = "20"


# ===============================================================
# == Node Colors
# ===============================================================

GRAY_FILL = "#cccccc77"
RECT_FILL = "#99999977"
BLACK = "#000000"
NODE_BORDER = "#444444"


# ===============================================================
# == Semantic Colors
# ===============================================================

OLIVE = "#afb200ff"
OLIVE_FILL = "#afb20019"
BLUE = "#00A2FF"
BLUE_FILL = "#00A2FF19"
GREEN = "#32bc00ff"
GREEN_FILL = "#32bc0019"
RED = "#EE220C"
STANDARDS_FILL = "#f27f72dc"


# ===============================================================
# == Classifier Icons
# ===============================================================

ICON_BY_KIND = {
    "actor": ("A", "#A9DCDF"),
    "class": ("C", "#ADD1B2"),
    "interface": ("I", "#B4A7E5"),
}
