"""Build native setup executables from the complete committed project."""

from __future__ import annotations

import argparse
import importlib
import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from apprc.distribution import (
    AppCapabilities,
    DistributionSpec,
    build_native_distribution,
    build_project_snapshot,
    inspect_capabilities,
    read_project_metadata,
)
from apprc.distribution.models import ProjectMetadata
from apprc.distribution.native import NativeTarget

from buildben_dev.packaging.release_manifest import validate_directory

TARGETS: tuple[NativeTarget, ...] = (
    "x86_64-unknown-linux-gnu",
    "x86_64-pc-windows-msvc",
)


def distribution_spec(root: Path, metadata: ProjectMetadata) -> DistributionSpec:
    """Read capabilities without introducing an application runtime dependency."""
    capabilities = AppCapabilities()
    if metadata.identity.apprc_reference is not None:
        module_name, object_name = metadata.identity.apprc_reference.split(":", 1)
        declaration = getattr(importlib.import_module(module_name), object_name)
        capabilities = inspect_capabilities(declaration)
    return DistributionSpec(metadata=metadata, capabilities=capabilities)


def build_artifacts(
    root: Path,
    *,
    revision: str = "HEAD",
    extras: tuple[str, ...] = (),
    targets: tuple[NativeTarget, ...] = TARGETS,
) -> tuple[Path, ...]:
    """Snapshot the selected committed workspace and publish native setup files."""
    root = root.resolve()
    metadata = read_project_metadata(root)
    spec = distribution_spec(root, metadata)
    cache = root / ".cache" / "apprc"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="project-snapshot-", dir=cache
    ) as temporary:
        project = build_project_snapshot(
            spec, revision=revision, destination=Path(temporary) / "project.zip"
        )
        command = os.environ.get("UV") or shutil.which("uv")
        if command is None:
            raise FileNotFoundError("Native authoring requires uv on PATH or UV.")
        uv = Path(command).expanduser().resolve(strict=True)
        native = build_native_distribution(
            spec,
            project,
            uv=uv,
            workspace=Path(temporary) / "native",
            targets=targets,
            extras=extras,
        )
    return (
        *(artifact.path for artifact in native.artifacts),
        native.checksums.project_root / native.checksums.destination,
    )


def check_artifacts(root: Path) -> tuple[str, ...]:
    """Validate declarations and final checksums without writing or rebuilding."""
    root = root.resolve()
    metadata = read_project_metadata(root)
    distribution_spec(root, metadata)
    return validate_directory(root / "dist", app_id=metadata.identity.app_id)


def main(argv: Sequence[str] | None = None) -> None:
    """Run native authoring or the read-only final-artifact validator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--extra", action="append", default=[])
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if arguments.check:
        print("\n".join(check_artifacts(root)))
    else:
        print(
            "\n".join(
                path.name
                for path in build_artifacts(
                    root,
                    revision=arguments.revision,
                    extras=tuple(arguments.extra),
                )
            )
        )


if __name__ == "__main__":
    main()
