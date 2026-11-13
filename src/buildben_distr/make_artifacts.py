"""Generate deterministic AppRC lifecycle artifacts for this application."""

from __future__ import annotations

import argparse
import importlib
import tomllib
from pathlib import Path, PurePosixPath
from typing import cast

from apprc.distribution import (
    AppCapabilities,
    Artifact,
    DistributionSpec,
    PayloadTree,
    generate_artifacts,
    install_support_files,
    inspect_capabilities,
    read_project_metadata,
    write_artifacts,
)
from apprc.distribution.models import ProjectMetadata


def _payload(root: Path, metadata: ProjectMetadata) -> PayloadTree:
    return PayloadTree(
        root / metadata.distribution_path / "payload",
        tuple(
            PurePosixPath("app_lifecycle") / name
            for name in ("__init__.py", "install.py", "uninstall.py", "actions.py")
        ),
    )


def distribution_spec(root: Path, metadata: ProjectMetadata) -> DistributionSpec:
    """Build application identity and capabilities without runtime overrides."""
    settings = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = cast(dict[str, object], settings["project"])
    capabilities = AppCapabilities()
    if metadata.identity.apprc_reference is not None:
        module_name, object_name = metadata.identity.apprc_reference.split(":", 1)
        declaration = getattr(importlib.import_module(module_name), object_name)
        capabilities = inspect_capabilities(declaration)
    urls = project.get("urls", {})
    repository = urls.get("Repository") if isinstance(urls, dict) else None
    if repository is None and metadata.identity.distribution == "buildben":
        repository = "https://github.com/HisQu/buildben.git"
    return DistributionSpec(
        metadata=metadata,
        capabilities=capabilities,
        repository_url=repository,
    )


def main() -> None:
    """Render authored payload and check or write its declared outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    metadata = read_project_metadata(root)
    spec = distribution_spec(root, metadata)
    base_payload = _payload(root, metadata)
    payload_root = metadata.distribution_path / "payload"
    resources: list[PurePosixPath] = []
    support_resources = []
    for relative, content in install_support_files(spec, base_payload).items():
        resource = PurePosixPath("app_lifecycle/_support") / relative
        support_resources.append(
            Artifact(
                payload_root / resource,
                content,
                relative.name in {"launch.sh", "uninstall.sh"},
                root,
            )
        )
        resources.append(resource)
    write_artifacts(support_resources, check=arguments.check)
    payload = PayloadTree(
        root / payload_root, base_payload.modules, resources=tuple(resources)
    )
    write_artifacts(generate_artifacts(spec, payload), check=arguments.check)


if __name__ == "__main__":
    main()
