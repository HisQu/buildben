"""Native release fixtures shared by maintained integrity/workflow tests."""

from __future__ import annotations

import io
import shutil
import tarfile
import zipfile
from pathlib import Path

from buildben_dev.packaging import release_manifest


def write_package_pair(
    directory: Path, *, distribution: str, version: str
) -> list[str]:
    """Write standard Python package fixtures independently of native assets."""
    stem = distribution.replace("-", "_")
    wheel_name = f"{stem}-{version}-py3-none-any.whl"
    metadata = (
        f"Metadata-Version: 2.1\nName: {distribution}\nVersion: {version}\n\n".encode()
    )
    with zipfile.ZipFile(directory / wheel_name, "w") as wheel:
        wheel.writestr(f"{stem}-{version}.dist-info/METADATA", metadata)
    sdist_name = f"{distribution}-{version}.tar.gz"
    with tarfile.open(directory / sdist_name, "w:gz") as archive:
        item = tarfile.TarInfo(f"{distribution}-{version}/PKG-INFO")
        item.size = len(metadata)
        archive.addfile(item, io.BytesIO(metadata))
    return [wheel_name, sdist_name]


def write_release_fixture(
    directory: Path,
    *,
    app_id: str,
    distribution: str,
    version: str,
    commit: str,
) -> list[str]:
    """Write the two native setup files and their exact SHA256SUMS."""
    del distribution, version, commit
    names = release_manifest.native_asset_names(app_id)
    payload = {
        name: f"Native setup fixture: {name}\n".encode()
        for name in names
        if name != release_manifest.CHECKSUMS_NAME
    }
    for name, content in payload.items():
        (directory / name).write_bytes(content)
    (directory / release_manifest.CHECKSUMS_NAME).write_bytes(
        release_manifest.checksum_bytes(payload, app_id=app_id)
    )
    return list(names)


def copy_release_tooling(
    project: Path,
    repository: Path,
    *,
    scaffold: bool,
    package: str = "buildben_dev",
) -> str:
    """Copy the actual canonical/scaffold CLI into an isolated consumer project.

    :param project: Temporary consumer project, not the source checkout.
    :param repository: Checked source repository containing both implementations.
    :param scaffold: Select authored templates instead of canonical helpers.
    :param package: Isolated consumer's development package name.
    :return: Module entry for subprocess execution with the consumer's PYTHONPATH.
    """
    target = project / "src" / package / "packaging"
    target.mkdir(parents=True)
    for directory in (target.parent, target):
        (directory / "__init__.py").write_text(
            '"""Isolated release tooling fixture."""\n', encoding="utf-8"
        )
    for filename in ("release_assets.py", "release_manifest.py", "release_notes.py"):
        source = (
            repository
            / "src/buildben/_templates_proj"
            / f"_src-dev-packaging-{filename}.tmpl"
            if scaffold
            else repository / "src" / "buildben_dev" / "packaging" / filename
        )
        shutil.copyfile(source, target / filename)
    return f"{package}.packaging.release_assets"
