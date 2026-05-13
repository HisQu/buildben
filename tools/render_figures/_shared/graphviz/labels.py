"""HTML-like label builders for Graphviz nodes and edges."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape

from _shared.graphviz.models import ClassifierNode, TextBox
from _shared.graphviz.theme import (
    FONT,
    FONT_SIZE,
    GRAY_FILL,
    ICON_BY_KIND,
    MONO_FONT,
)


# ===============================================================
# == Classifier Labels
# ===============================================================


def classifier_label(spec: ClassifierNode) -> str:
    """Build a Graphviz HTML label for one classifier node.

    :param spec: Node content and visual style.
    :return: HTML-like label accepted by Graphviz.
    """

    icon, icon_fill = ICON_BY_KIND[spec.kind]
    border = str(spec.border_width)
    border_color = spec.border_color if spec.border_width else "transparent"
    members = "".join(member_line(member) for member in spec.members)
    member_block = ""
    if members:
        member_block = (
            f'<TR><TD ALIGN="LEFT" BALIGN="LEFT" CELLPADDING="7">{members}</TD></TR>'
        )

    return f"""<
<TABLE BORDER="{border}" CELLBORDER="{border}" CELLSPACING="0" CELLPADDING="0" COLOR="{border_color}" BGCOLOR="{GRAY_FILL}" STYLE="rounded">
  <TR>
    <TD CELLPADDING="7">
      <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">
        <TR>
          <TD BORDER="1" COLOR="#181818" BGCOLOR="{icon_fill}"><FONT POINT-SIZE="16">{icon}</FONT></TD>
          <TD WIDTH="8"></TD>
          <TD>{stereotype_html(spec.stereotype)}<BR/>{title_html(spec.title, italic=spec.title_italic)}</TD>
        </TR>
      </TABLE>
    </TD>
  </TR>
  {member_block}
</TABLE>
>"""


def stereotype_html(stereotype: str) -> str:
    """Render one classifier label line.

    :param stereotype: Classifier text without guillemets.
    :return: Escaped HTML-like text.
    """

    return f'<FONT POINT-SIZE="{FONT_SIZE}"><I>&laquo;{escape(stereotype)}&raquo;</I></FONT>'


def title_html(title: str, *, italic: bool) -> str:
    """Render a possibly multi-line title.

    :param title: Title text.
    :param italic: Whether the title should be italic.
    :return: Escaped HTML-like text.
    """

    lines = [escape(line) for line in title.splitlines()]
    text = "<BR/>".join(lines)
    if italic:
        return f'<FONT POINT-SIZE="{FONT_SIZE}"><B><I>{text}</I></B></FONT>'
    return f'<FONT POINT-SIZE="{FONT_SIZE}"><B>{text}</B></FONT>'


def member_line(text: str) -> str:
    """Render one classifier member row.

    :param text: Row text.
    :return: Escaped HTML-like text with a green public marker.
    """

    return (
        f'<FONT POINT-SIZE="{FONT_SIZE}" COLOR="#038048">&#8728;</FONT>'
        f'<FONT POINT-SIZE="{FONT_SIZE}"> {escape(text)}</FONT><BR ALIGN="LEFT"/>'
    )


# ===============================================================
# == Text Box Labels
# ===============================================================


def text_box_label(spec: TextBox) -> str:
    """Build a Graphviz HTML label for one rounded text block.

    :param spec: Text content and visual style.
    :return: HTML-like label accepted by Graphviz.
    """

    body_font = MONO_FONT if spec.monospace else FONT
    rows = "".join(text_line(row, font=body_font) for row in spec.rows)
    return f"""<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" BGCOLOR="{spec.fill}" STYLE="rounded">
  <TR><TD ALIGN="LEFT" CELLPADDING="10"><FONT POINT-SIZE="{FONT_SIZE}"><B>{escape(spec.title)}</B></FONT></TD></TR>
  {rows}
</TABLE>
>"""


def text_line(text: str, *, font: str = FONT) -> str:
    """Render one line inside a simple text box.

    :param text: Row text.
    :param font: Font family for the row.
    :return: Escaped HTML-like table row.
    """

    return (
        f'<TR><TD ALIGN="LEFT" CELLPADDING="4"><FONT FACE="{font}" POINT-SIZE="{FONT_SIZE}">'
        f"{escape_html_text(text)}</FONT></TD></TR>"
    )


def escape_html_text(text: str) -> str:
    """Escape text while preserving explicit numeric entities.

    :param text: Text that may include ``&#8226;`` bullet entities.
    :return: Graphviz-safe HTML-like text.
    """

    return escape(text).replace("&amp;#8226;", "&#8226;")


# ===============================================================
# == Edge Labels
# ===============================================================


def edge_label(lines: str | Iterable[str], *, bold: bool = False) -> str:
    """Build an italic HTML-like edge label.

    :param lines: Label text or line sequence.
    :param bold: Whether to apply bold emphasis.
    :return: HTML-like label accepted by Graphviz.
    """

    if isinstance(lines, str):
        parts = lines.splitlines()
    else:
        parts = list(lines)
    body = "<BR/>".join(escape(part) for part in parts)
    if bold:
        return f'<<FONT POINT-SIZE="{FONT_SIZE}"><I><B>{body}</B></I></FONT>>'
    return f'<<FONT POINT-SIZE="{FONT_SIZE}"><I>{body}</I></FONT>>'
