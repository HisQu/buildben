"""Package and release fixtures shared by maintained integrity/workflow tests."""

from __future__ import annotations

import io
import tarfile
import shutil
import zipfile
from pathlib import Path

from buildben_dev.packaging import release_manifest


def write_package_pair(
    directory: Path, *, distribution: str, version: str
) -> list[str]:
    """Write bounded package metadata fixtures for release validation.

    :param directory: Existing isolated release directory.
    :param distribution: Expected package identity.
    :param version: Explicit fixture version.
    :return: Wheel and sdist names, in that order.
    """
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
    """Write a complete package/helper integrity fixture without any publication.

    :param directory: Existing isolated release directory.
    :param app_id: Persistent application identity.
    :param distribution: Normalized package identity.
    :param version: Explicit package/release version.
    :param commit: Immutable test source identity.
    :return: Exact package/native/manifest filenames.
    """
    names = write_package_pair(directory, distribution=distribution, version=version)
    native = tuple(
        f"{app_id}-{action}-{platform}"
        for action in ("install", "launch")
        for platform in ("linux-x86_64", "windows-x86_64.exe")
    )
    names.extend(native)
    names.extend(release_manifest.SCRIPT_SUPPORT)
    for name in names[2:]:
        (directory / name).write_bytes(f"Owned native release asset: {name}\n".encode())
    payload = {name: (directory / name).read_bytes() for name in names}
    content = release_manifest.manifest_bytes(
        payload,
        app_id=app_id,
        distribution=distribution,
        version=version,
        commit=commit,
    )
    (directory / release_manifest.MANIFEST_NAME).write_bytes(content)
    names.append(release_manifest.MANIFEST_NAME)
    return names


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
