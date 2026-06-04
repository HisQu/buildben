"""Render the full Buildben dependency-management figure."""

from __future__ import annotations

from pathlib import Path

from _buildben_figures import (
    DEPENDENCY_MANAGEMENT_POLICY,
    build_dependency_management,
    export_single_graph_figure,
    run_single_graph_cli,
)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent
FIGURE_NAME = "diagram-graphviz"


def export_figure(
    output_dir: Path | None = None,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Render the figure to SVG and PNG files.

    :param output_dir: Optional directory receiving generated files.
    :return: Generated SVG paths and PNG paths.
    """

    return export_single_graph_figure(
        build_dependency_management(),
        FIGURE_NAME,
        default_output_dir=DEFAULT_OUTPUT_DIR,
        output_dir=output_dir,
        size_policy=DEPENDENCY_MANAGEMENT_POLICY,
    )


def main() -> int:
    """Run the command-line exporter.

    :return: Process exit code.
    """

    return run_single_graph_cli(
        export_figure,
        description="Render the full Buildben dependency-management figure.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
