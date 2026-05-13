"""Render Graphviz reproductions of the PlantUML reference figures.

The existing ``.puml`` diagrams use PlantUML package boxes with a tabbed
folder header. Graphviz clusters do not expose that exact package shape, so
this script keeps the same color language, typography scale, relationships,
and rounded grouping feel with pure Graphviz clusters instead.

:return: SVG and PNG files beside the matching PlantUML outputs, using the
    ``-graphviz`` filename suffix.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from html import escape
from pathlib import Path

from graphviz import Digraph


# ===============================================================
# == Paths
# ===============================================================

FIGURES_DIR = Path(__file__).resolve().parent


# ===============================================================
# == Visual constants
# ===============================================================

FONT = "sans-serif"
MONO_FONT = "monospace"
FONT_SIZE = "20"

GRAY_FILL = "#cccccc77"
RECT_FILL = "#99999977"
BLACK = "#000000"
NODE_BORDER = "#444444"

OLIVE = "#afb200ff"
OLIVE_FILL = "#afb20019"
BLUE = "#00A2FF"
BLUE_FILL = "#00A2FF19"
GREEN = "#32bc00ff"
GREEN_FILL = "#32bc0019"
RED = "#EE220C"
STANDARDS_FILL = "#f27f72dc"

ICON_BY_KIND = {
    "actor": ("A", "#A9DCDF"),
    "class": ("C", "#ADD1B2"),
    "interface": ("I", "#B4A7E5"),
}


@dataclass(frozen=True)
class UmlNode:
    """Describe one UML-like node rendered as an HTML table.

    :param title: Main bold label shown in the node header.
    :param stereotype: PlantUML-style classifier shown above the title.
    :param members: Body rows shown below the header.
    :param kind: Icon color family; one of ``actor``, ``class``, or
        ``interface``.
    :param border_color: Border color used for the table cells.
    :param border_width: ``0`` for the borderless file/config look.
    :param title_italic: Whether to italicize the title.
    """

    title: str
    stereotype: str
    members: tuple[str, ...] = ()
    kind: str = "class"
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


def main() -> None:
    """Render all Graphviz reproductions.

    :return: ``None``. The function writes image files below
        :data:`FIGURES_DIR`.
    """

    render_figure(build_full_diagram(), "diagram")
    render_figure(build_simple_diagram(), "diagram-simple")
    render_figure(build_graphical_abstract(), "graphical-abstract_init-proj")


def new_graph(name: str, *, rankdir: str = "LR") -> Digraph:
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


def render_figure(graph: Digraph, figure_name: str) -> None:
    """Render one graph as SVG and PNG.

    :param graph: Diagram to render.
    :param figure_name: Figure directory and base name shared with PlantUML.
    :return: ``None``. Graphviz writes the files.
    """

    output_dir = FIGURES_DIR / figure_name
    output_name = f"{figure_name}-graphviz"
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


def add_package(
    graph: Digraph,
    name: str,
    label: str,
    stereotype: str,
    color: str,
    fill: str,
) -> Digraph:
    """Create a rounded Graphviz cluster used as a package substitute.

    :param graph: Parent graph. The parameter documents ownership; attach the
        returned cluster with :meth:`graphviz.Digraph.subgraph` after adding
        nodes to it.
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
    :param stereotype: PlantUML-style classifier.
    :return: Escaped Graphviz label text.
    """

    return f"{label}\n<<{stereotype}>>"


def add_uml_node(graph: Digraph, node_id: str, spec: UmlNode) -> None:
    """Add one UML-like node to a graph.

    :param graph: Target graph or cluster.
    :param node_id: DOT identifier.
    :param spec: Node content and style.
    :return: ``None``.
    """

    graph.node(node_id, label=uml_label(spec))


def add_text_box(graph: Digraph, node_id: str, spec: TextBox) -> None:
    """Add one rounded multi-line text box.

    :param graph: Target graph or cluster.
    :param node_id: DOT identifier.
    :param spec: Text content and visual style.
    :return: ``None``.
    """

    graph.node(node_id, label=text_box_label(spec))


def uml_label(spec: UmlNode) -> str:
    """Build a Graphviz HTML label for one UML-like node.

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


def stereotype_html(stereotype: str) -> str:
    """Render one stereotype line.

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
    """Render one UML member row.

    :param text: Row text.
    :return: Escaped HTML-like text with a green public marker.
    """

    return (
        f'<FONT POINT-SIZE="{FONT_SIZE}" COLOR="#038048">&#8728;</FONT>'
        f'<FONT POINT-SIZE="{FONT_SIZE}"> {escape(text)}</FONT><BR ALIGN="LEFT"/>'
    )


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
    :param dashed: Whether to use the red dependency dash pattern.
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


def build_full_diagram() -> Digraph:
    """Build the full dependency-management diagram.

    :return: Configured Graphviz diagram.
    """

    graph = new_graph("diagram_graphviz")
    graph.attr(nodesep="0.55", ranksep="0.85", splines="polyline")

    ge = add_package(
        graph,
        "GE",
        "Operating System",
        "Global Environment",
        OLIVE,
        OLIVE_FILL,
    )
    add_uml_node(
        ge,
        "UVG",
        UmlNode(
            "uv",
            "CLI",
            ("tool install()", "tool run()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )
    add_uml_node(
        ge,
        "B",
        UmlNode(
            "buildben",
            "CLI",
            ("init-proj()", "add-experiment()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )
    add_uml_node(
        ge,
        "D",
        UmlNode(
            "Direnv",
            "CLI",
            ("layout()", "direnv reload()", "direnv exec()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )
    add_uml_node(
        ge,
        "J",
        UmlNode("just", "CLI", (), "interface", BLACK, 1, True),
    )

    pdir = add_package(graph, "PDIR", "Project Directory", "Directory", BLUE, BLUE_FILL)
    add_uml_node(
        pdir,
        "PPRT",
        UmlNode(
            "pyproject.toml",
            "Config",
            ("Dependencies", "Setup Configuration"),
            "class",
            BLACK,
            0,
        ),
    )
    add_uml_node(
        pdir,
        "LOCK",
        UmlNode(
            "uv.lock\npylock.toml",
            "Lock-Files",
            ("Dependencies", "Versions & Sources"),
            "class",
            BLACK,
            0,
        ),
    )
    add_uml_node(
        pdir,
        "ERC",
        UmlNode(".envrc", "Config", ("PROJECT_NAME", "ENV_VARS"), "class", BLACK, 0),
    )
    add_uml_node(
        pdir,
        "JF",
        UmlNode("justfile", "Recipes", ("reset()", "install-deps()", "...()"), "class"),
    )

    venv = add_package(graph, "VENV", ".venv", "Virtual Environment", GREEN, GREEN_FILL)
    add_uml_node(
        venv,
        "UVV",
        UmlNode(
            "uv",
            "Tool",
            ("venv()", "lock()", "sync()", "run()"),
            "interface",
            NODE_BORDER,
            1,
            True,
        ),
    )
    add_uml_node(
        venv,
        "PD",
        UmlNode("python dependencies", "Pkg", (), "class", BLACK, 0),
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


def build_simple_diagram() -> Digraph:
    """Build the simplified dependency-management diagram.

    :return: Configured Graphviz diagram.
    """

    graph = new_graph("diagram_simple_graphviz")
    graph.attr(nodesep="0.7", ranksep="1.05")

    ge = add_package(
        graph,
        "GE",
        "Operating System",
        "Global Environment",
        OLIVE,
        OLIVE_FILL,
    )
    add_uml_node(
        ge,
        "UV",
        UmlNode(
            "uv",
            "CLI",
            ("python install()", "venv()", "lock()", "sync()", "run()"),
            "interface",
            BLACK,
            1,
            True,
        ),
    )

    pdir = add_package(graph, "PDIR", "Project Directory", "Directory", BLUE, BLUE_FILL)
    add_uml_node(
        pdir,
        "APP",
        UmlNode("main.py\n(or other code)", "File", (), "class", BLACK, 0),
    )
    add_uml_node(
        pdir,
        "PPRT",
        UmlNode(
            "pyproject.toml",
            "Config",
            ("Dependencies", "Project Metadata"),
            "class",
            BLACK,
            0,
        ),
    )
    add_uml_node(
        pdir,
        "LOCK",
        UmlNode(
            "uv.lock",
            "Lock-File",
            ("Dependencies", "Versions", "Sources"),
            "class",
            BLACK,
            0,
        ),
    )

    add_uml_node(
        graph,
        "USER",
        UmlNode(
            "User",
            "Actor",
            ("eat()", "sleep()", "code()"),
            "actor",
            NODE_BORDER,
            1,
            True,
        ),
    )

    venv = add_package(graph, "VENV", ".venv", "Virtual Environment", GREEN, GREEN_FILL)
    add_uml_node(
        venv,
        "PKG",
        UmlNode("Python Dependencies", "Pkg", (), "class", BLACK, 0),
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


def build_graphical_abstract() -> Digraph:
    """Build the graphical abstract for ``bube init-proj``.

    :return: Configured Graphviz diagram.
    """

    graph = new_graph("graphical_abstract_init_proj_graphviz")
    graph.attr(nodesep="0.85", ranksep="1.0")

    buildben = add_package(graph, "BB", "buildben", "Python Package", OLIVE, OLIVE_FILL)
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
        buildben, "BBinitcli", TextBox("$ bube init-proj", (), RECT_FILL, True)
    )

    project = add_package(
        graph, "P", "Project", "Directory & Environment", BLUE, BLUE_FILL
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


if __name__ == "__main__":
    main()
