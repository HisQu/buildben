"""Stage only the final native setups and SDK SHA256SUMS."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from apprc.distribution import read_project_metadata
from apprc.distribution.native import NativeTarget

from buildben_dev.packaging import release_assets
from buildben_dev.packaging.release_manifest import validate_directory
from buildben_distr.make_artifacts import TARGETS, build_artifacts

REPOSITORY = "HisQu/buildben"


def stage_release(
    tag: str,
    commit: str,
    *,
    root: Path,
    repository: str = REPOSITORY,
    extras: tuple[str, ...] = (),
    targets: tuple[NativeTarget, ...] = TARGETS,
) -> tuple[str, ...]:
    """Build the committed snapshot and copy only validated native release assets."""
    root = root.resolve()
    if root != Path.cwd().resolve():
        raise ValueError("Run release staging from the application repository root.")
    metadata = read_project_metadata(root)
    release_assets.Identity(
        release_assets._repository(repository),
        release_assets._tag(tag),
        release_assets._sha(commit),
    )
    if tag != f"v{metadata.version}":
        raise ValueError("Release tag does not match project metadata.")
    built = build_artifacts(root, revision=commit, extras=extras, targets=targets)
    names = tuple(path.name for path in built)
    destination = root / "release" / "assets"
    if destination.is_symlink():
        raise ValueError("Release staging directory cannot be linked.")
    destination.mkdir(parents=True, exist_ok=True)
    if {path.name for path in destination.iterdir()} - set(names):
        raise ValueError(
            "Release staging directory contains stale or unexpected files."
        )
    for name in names:
        target = destination / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"Release staging output is not a regular file: {name}.")
        shutil.copyfile(root / "dist" / name, target)
        if name.endswith("linux-x86_64"):
            target.chmod(0o755)
    return validate_directory(destination, app_id=metadata.identity.app_id, exact=True)


def main() -> None:
    """Parse immutable release identity and stage exact SDK outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("commit")
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--extra", action="append", default=[])
    arguments = parser.parse_args()
    print(
        "\n".join(
            stage_release(
                arguments.tag,
                arguments.commit,
                root=Path.cwd(),
                repository=arguments.repository,
                extras=tuple(arguments.extra),
            )
        )
    )


if __name__ == "__main__":
    main()
