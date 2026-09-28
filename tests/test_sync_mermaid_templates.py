"""Checks for the Graphigs-to-Buildben Mermaid template sync command."""

from __future__ import annotations

from pathlib import Path

from buildben_dev.sync_mermaid_templates import sync_templates


def test_sync_mermaid_templates_check_is_read_only(tmp_path: Path) -> None:
    """Check mode reports drift without creating or changing snapshot files.

    :param tmp_path: Temporary directory used for sync snapshots.
    :return: None.
    """
    sources = {
        "flowchart": "---\ntitle: {my_project}\n---\nflowchart LR\n",
        "class-diagram": "---\ntitle: {MyProject}\n---\nclassDiagram\n",
    }

    def template_source(kind: str) -> str:
        return sources[kind]

    assert sync_templates(template_source, tmp_path, check=True) == 1
    assert list(tmp_path.iterdir()) == []

    assert sync_templates(template_source, tmp_path) == 0
    snapshot = {
        path.name: path.read_text(encoding="utf-8") for path in tmp_path.iterdir()
    }
    assert sync_templates(template_source, tmp_path, check=True) == 0

    sources["flowchart"] = "---\ntitle: Updated\n---\nflowchart LR\n"
    assert sync_templates(template_source, tmp_path, check=True) == 1
    assert {
        path.name: path.read_text(encoding="utf-8") for path in tmp_path.iterdir()
    } == snapshot
