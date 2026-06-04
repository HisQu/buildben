"""Buildben README and presentation figure builders."""

# ruff: noqa: E402

from __future__ import annotations

from pathlib import Path
import sys


def _add_sibling_graphigs_source_path() -> None:
    """Make local figure scripts work before Graphigs is installed.

    :return: ``None``.
    """

    graphigs_src = Path(__file__).resolve().parents[3] / "graphigs" / "src"
    graphigs_src_text = str(graphigs_src)
    if graphigs_src.is_dir() and graphigs_src_text not in sys.path:
        sys.path.insert(0, graphigs_src_text)


_add_sibling_graphigs_source_path()

from graphviz.graphs import Digraph

from graphigs.figure_contract import (
    exempt_figure,
)
from graphigs.graphviz import (
    export_single_graph_figure,
    run_single_graph_cli,
)
import graphigs as gg


DEPENDENCY_MANAGEMENT_POLICY = exempt_figure(
    "The Buildben dependency-management figure preserves the original wide "
    "architecture layout."
)
DEPENDENCY_MANAGEMENT_SIMPLE_POLICY = exempt_figure(
    "The simplified Buildben dependency-management figure preserves the "
    "original wide architecture layout."
)
PROJECT_SCAFFOLD_POLICY = exempt_figure(
    "The Buildben project-scaffold figure preserves the original wide "
    "graphical abstract layout."
)


def build_dependency_management() -> Digraph:
    """Build the full dependency-management diagram.

    :return: Configured Graphviz diagram.
    """

    figure = gg.diagram("diagram_graphviz")
    figure.graph.attr(nodesep="0.55", ranksep="0.85", splines="polyline")
    _add_full_global_environment(figure)
    _add_full_project_directory(figure)
    _add_full_virtual_environment(figure)
    _add_full_rank_guides(figure)
    _add_full_build_edges(figure)
    _add_full_environment_edges(figure)
    _add_full_requirement_edges(figure)
    return figure.graph


def _add_full_global_environment(figure: gg.Diagram) -> None:
    """Add globally installed CLI tools to the full Buildben diagram.

    :param figure: Diagram receiving the cluster.
    :return: ``None``.
    """

    with figure.group(
        "GE",
        "Operating System",
        color=gg.OLIVE,
        fill=gg.OLIVE_GROUP_FILL,
        stereotype="Global Environment",
    ) as group:
        group.classifier(
            "UVG",
            "uv",
            "tool install()",
            "tool run()",
            stereotype="CLI",
            kind="interface",
            border_color=gg.BLACK,
            title_italic=True,
        )
        group.classifier(
            "B",
            "buildben",
            "init-proj()",
            "add-experiment()",
            stereotype="CLI",
            kind="interface",
            border_color=gg.BLACK,
            title_italic=True,
        )
        group.classifier(
            "D",
            "Direnv",
            "layout()",
            "direnv reload()",
            "direnv exec()",
            stereotype="CLI",
            kind="interface",
            border_color=gg.BLACK,
            title_italic=True,
        )
        group.classifier(
            "J",
            "just",
            stereotype="CLI",
            kind="interface",
            border_color=gg.BLACK,
            title_italic=True,
        )


def _add_full_project_directory(figure: gg.Diagram) -> None:
    """Add project-owned files to the full Buildben diagram.

    :param figure: Diagram receiving the cluster.
    :return: ``None``.
    """

    with figure.group(
        "PDIR",
        "Project Directory",
        color=gg.BLUE,
        fill=gg.BLUE_GROUP_FILL,
        stereotype="Directory",
    ) as group:
        group.classifier(
            "PPRT",
            "pyproject.toml",
            "Dependencies",
            "Setup Configuration",
            stereotype="Config",
            border_color=gg.BLACK,
            border_width=0,
        )
        group.classifier(
            "LOCK",
            "uv.lock\npylock.toml",
            "Dependencies",
            "Versions & Sources",
            stereotype="Lock-Files",
            border_color=gg.BLACK,
            border_width=0,
        )
        group.classifier(
            "ERC",
            ".envrc",
            "PROJECT_NAME",
            "ENV_VARS",
            stereotype="Config",
            border_color=gg.BLACK,
            border_width=0,
        )
        group.classifier(
            "JF",
            "justfile",
            "reset()",
            "install-deps()",
            "...()",
            stereotype="Recipes",
        )


def _add_full_virtual_environment(figure: gg.Diagram) -> None:
    """Add the project virtual environment to the full Buildben diagram.

    :param figure: Diagram receiving the cluster.
    :return: ``None``.
    """

    with figure.group(
        "VENV",
        ".venv",
        color=gg.GREEN,
        fill=gg.GREEN_GROUP_FILL,
        stereotype="Virtual Environment",
    ) as group:
        group.classifier(
            "UVV",
            "uv",
            "venv()",
            "lock()",
            "sync()",
            "run()",
            stereotype="Tool",
            kind="interface",
            title_italic=True,
        )
        group.classifier(
            "PD",
            "python dependencies",
            stereotype="Pkg",
            border_color=gg.BLACK,
            border_width=0,
        )


def _add_full_rank_guides(figure: gg.Diagram) -> None:
    """Add invisible edges that keep the full diagram readable.

    :param figure: Diagram receiving the layout hints.
    :return: ``None``.
    """

    figure.hidden_edge("UVG", "B")
    figure.hidden_edge("B", "PPRT")
    figure.hidden_edge("PPRT", "UVV")
    figure.hidden_edge("UVV", "PD")


def _add_full_build_edges(figure: gg.Diagram) -> None:
    """Draw project creation and lock-file update flows.

    :param figure: Diagram receiving the edges.
    :return: ``None``.
    """

    figure.edge("UVG", "B", ("installs", "as tool"), color=gg.OLIVE)
    figure.edge(
        "B",
        "PPRT",
        ("copies templates", "(cookiecutter)"),
        color=gg.BLUE,
        penwidth="4",
    )
    figure.edge("UVV", "LOCK", ("resolves", "& exports"), color=gg.BLUE)
    figure.edge(
        "UVV",
        "PPRT",
        "editable install",
        color=gg.BLUE,
        constraint=False,
    )


def _add_full_environment_edges(figure: gg.Diagram) -> None:
    """Draw virtual-environment creation and activation flows.

    :param figure: Diagram receiving the edges.
    :return: ``None``.
    """

    figure.edge("UVG", "UVV", ("creates", ".venv"), color=gg.GREEN, penwidth="4")
    figure.edge("UVV", "PD", "syncs", color=gg.GREEN)
    figure.edge("ERC", "UVV", "activates", color=gg.GREEN, constraint=False)
    figure.edge("JF", "UVV", "runs", color=gg.GREEN)


def _add_full_requirement_edges(figure: gg.Diagram) -> None:
    """Draw dashed prerequisite and read-dependency relationships.

    :param figure: Diagram receiving the edges.
    :return: ``None``.
    """

    figure.edge("ERC", "D", "requires", color=gg.RED, dashed=True)
    figure.edge("JF", "J", "requires", color=gg.RED, dashed=True)
    figure.edge("JF", "D", "requires", color=gg.RED, dashed=True)
    figure.edge("UVV", "PPRT", "reads dependency specs", color=gg.RED, dashed=True)


def build_dependency_management_simple() -> Digraph:
    """Build the simplified dependency-management diagram.

    :return: Configured Graphviz diagram.
    """

    figure = gg.diagram("diagram_simple_graphviz")
    figure.graph.attr(nodesep="0.7", ranksep="1.05")
    _add_simple_global_environment(figure)
    _add_simple_project_directory(figure)
    _add_simple_virtual_environment(figure)
    figure.classifier(
        "USER",
        "User",
        "uses uv",
        "reviews locks",
        "codes",
        stereotype="Actor",
        kind="actor",
        title_italic=True,
    )
    figure.hidden_edge("UV", "PPRT")
    figure.hidden_edge("PPRT", "USER")
    figure.hidden_edge("USER", "PKG")
    figure.edge("USER", "PPRT", "edits", color=gg.BLUE, constraint=False)
    figure.edge("UV", "LOCK", "resolves", color=gg.BLUE, constraint=False)
    figure.edge("USER", "LOCK", "reviews", color=gg.BLUE, constraint=False)
    figure.edge(
        "UV",
        "PKG",
        ("creates .venv", "& syncs"),
        color=gg.GREEN,
        penwidth="4",
        constraint=False,
    )
    figure.edge("USER", "PKG", "uses uv", color=gg.GREEN, constraint=False)
    figure.edge("APP", "PKG", "requires", color=gg.RED, dashed=True)
    figure.edge("UV", "PPRT", "requires", color=gg.RED, dashed=True)
    figure.edge("UV", "LOCK", "reads", color=gg.RED, dashed=True)
    return figure.graph


def _add_simple_global_environment(figure: gg.Diagram) -> None:
    """Add the host ``uv`` CLI to the simplified Buildben diagram.

    :param figure: Diagram receiving the cluster.
    :return: ``None``.
    """

    with figure.group(
        "GE",
        "Operating System",
        color=gg.OLIVE,
        fill=gg.OLIVE_GROUP_FILL,
        stereotype="Global Environment",
    ) as group:
        group.classifier(
            "UV",
            "uv",
            "python install()",
            "venv()",
            "lock()",
            "sync()",
            "run()",
            stereotype="CLI",
            kind="interface",
            border_color=gg.BLACK,
            title_italic=True,
        )


def _add_simple_project_directory(figure: gg.Diagram) -> None:
    """Add project files to the simplified Buildben diagram.

    :param figure: Diagram receiving the cluster.
    :return: ``None``.
    """

    with figure.group(
        "PDIR",
        "Project Directory",
        color=gg.BLUE,
        fill=gg.BLUE_GROUP_FILL,
        stereotype="Directory",
    ) as group:
        group.classifier(
            "APP",
            "main.py\n(or other code)",
            stereotype="File",
            border_color=gg.BLACK,
            border_width=0,
        )
        group.classifier(
            "PPRT",
            "pyproject.toml",
            "Dependencies",
            "Project Metadata",
            stereotype="Config",
            border_color=gg.BLACK,
            border_width=0,
        )
        group.classifier(
            "LOCK",
            "uv.lock",
            "Dependencies",
            "Versions",
            "Sources",
            stereotype="Lock-File",
            border_color=gg.BLACK,
            border_width=0,
        )


def _add_simple_virtual_environment(figure: gg.Diagram) -> None:
    """Add the synced package node to the simplified Buildben diagram.

    :param figure: Diagram receiving the cluster.
    :return: ``None``.
    """

    with figure.group(
        "VENV",
        ".venv",
        color=gg.GREEN,
        fill=gg.GREEN_GROUP_FILL,
        stereotype="Virtual Environment",
    ) as group:
        group.classifier(
            "PKG",
            "Python Dependencies",
            stereotype="Pkg",
            border_color=gg.BLACK,
            border_width=0,
        )


def build_project_scaffold() -> Digraph:
    """Build the graphical abstract for ``bube init-proj``.

    :return: Configured Graphviz diagram.
    """

    figure = gg.diagram("graphical_abstract_init_proj_graphviz")
    figure.graph.attr(nodesep="0.85", ranksep="1.0")
    with figure.group(
        "BB",
        "buildben",
        color=gg.OLIVE,
        fill=gg.OLIVE_GROUP_FILL,
        stereotype="Python Package",
    ) as group:
        group.text(
            "TEMP",
            "Templates:",
            "&#8226; pyproject.toml",
            "&#8226; .envrc",
            "&#8226; justfile",
            "&#8226; ...",
            monospace=True,
        )
        group.text("BBinitcli", "$ bube init-proj", monospace=True)
    with figure.group(
        "P",
        "Project",
        color=gg.BLUE,
        fill=gg.BLUE_GROUP_FILL,
        stereotype="Directory & Environment",
    ) as group:
        group.text(
            "Tools",
            "Universal Tools:",
            "&#8226; direnv",
            "&#8226; just",
            "&#8226; ...",
            monospace=True,
        )
        group.text(
            "PyTools",
            "Python Tools:",
            "&#8226; uv sync",
            "&#8226; uv.lock",
            "&#8226; .venv",
            "&#8226; ...",
            monospace=True,
        )
    figure.text(
        "Standards",
        "Python Standards:",
        "&#8226; PEP 405: Virtual-environment",
        "&#8226; PEP 621: pyproject.toml",
        "&#8226; PEP 660: Editable install",
        "&#8226; PEP 751: Lock-files",
        "&#8226; uv: uv.lock workflow",
        "&#8226; PyPA: src/-Layout",
        fill=gg.NODE_SURFACE_FILL,
        border_color=gg.ORANGE,
        monospace=True,
    )
    figure.edge("TEMP", "BBinitcli", "copied by", color=gg.OLIVE)
    figure.edge(
        "BBinitcli",
        "Tools",
        ("creates scaffold", "no runtime dep"),
        color=gg.BLUE,
        penwidth="4",
    )
    figure.edge("Tools", "PyTools", ("automate", "& simplify"), color=gg.BLUE)
    figure.edge(
        "PyTools",
        "Standards",
        "comply with",
        color=gg.RED,
        dashed=True,
        constraint=False,
    )
    figure.edge(
        "TEMP",
        "Standards",
        "comply with",
        color=gg.RED,
        dashed=True,
        constraint=False,
    )
    return figure.graph


__all__ = [
    "DEPENDENCY_MANAGEMENT_POLICY",
    "DEPENDENCY_MANAGEMENT_SIMPLE_POLICY",
    "PROJECT_SCAFFOLD_POLICY",
    "build_dependency_management",
    "build_dependency_management_simple",
    "build_project_scaffold",
    "export_single_graph_figure",
    "run_single_graph_cli",
]
