"""Behavioral checks for release payload identity and safe archive metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from buildben_dev.packaging.installation_bundle import validate_manifest


def _manifest() -> dict[str, Any]:
    """Return a structurally valid manifest with no external files."""
    files = {
        "application_wheel": {
            "filename": "app-1.2.3-py3-none-any.whl",
            "sha256": "a" * 64,
        },
        "source_archive": {"filename": "app-1.2.3.tar.gz", "sha256": "b" * 64},
        "runtime_lock": {"filename": "runtime-requirements.txt", "sha256": "c" * 64},
        "runtime_constraints": {
            "filename": "runtime-constraints.txt",
            "sha256": "d" * 64,
        },
    }
    platforms = {
        "windows-x86_64": "app-1.2.3-windows-x86_64.zip",
        "linux-x86_64": "app-1.2.3-linux-x86_64.tar.gz",
        "macos-arm64": "app-1.2.3-macos-arm64.tar.gz",
    }
    return {
        "schema_version": 1,
        "project": "app",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repository": "owner/app",
        "commit_sha": "1" * 40,
        "python_requires": ">=3.12",
        **files,
        "platforms": platforms,
        "archive_members": {
            target: sorted(
                [
                    "install_release.py",
                    "install-windows.cmd",
                    "install-windows.ps1",
                    "prepare-powershell-windows.cmd",
                    "release-manifest.json",
                    "runtime-constraints.txt",
                    "runtime-requirements.txt",
                ]
                if target == "windows-x86_64"
                else [
                    "install-linux-macos.sh",
                    "install_release.py",
                    "release-manifest.json",
                    "runtime-constraints.txt",
                    "runtime-requirements.txt",
                ]
                + (["install-macos.command"] if target == "macos-arm64" else [])
            )
            for target in platforms
        },
    }


def test_validate_manifest_accepts_exact_source_and_platform_matrix() -> None:
    manifest = _manifest()
    assert validate_manifest(manifest, "owner/app", "1" * 40) is manifest


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(tag="v9.9.9"),
        lambda value: value.update(commit_sha="2" * 40),
        lambda value: value["runtime_lock"].update(filename="../runtime.txt"),
        lambda value: value["application_wheel"].update(sha256="not-a-digest"),
        lambda value: value["archive_members"]["linux-x86_64"].append("../escape"),
    ],
)
def test_validate_manifest_rejects_unsafe_or_inconsistent_metadata(change) -> None:
    manifest = _manifest()
    change(manifest)
    with pytest.raises(ValueError):
        validate_manifest(manifest, "owner/app", "1" * 40)


def test_runtime_exports_preserve_hashes_and_reject_local_or_credentialed_pins() -> (
    None
):
    from buildben_dev.packaging.installation_bundle import _safe_export

    original = b"Package[agent]==1.2.3 --hash=sha256:abc\n"
    assert _safe_export(original.decode(), constraints=False) == original
    assert (
        _safe_export(original.decode(), constraints=True)
        == b"Package==1.2.3 --hash=sha256:abc\n"
    )
    with pytest.raises(ValueError, match="credential-bearing"):
        _safe_export("dep @ https://user:secret@example.invalid/repo.git\n")
    with pytest.raises(ValueError, match="local/editable"):
        _safe_export("dep @ file:///home/private/project\n")


def test_archive_contains_only_validated_manifest_members(tmp_path) -> None:
    import hashlib
    import json
    import tarfile
    from buildben_dev.packaging.installation_bundle import archive

    release = tmp_path / "release"
    release.mkdir()
    manifest = _manifest()
    contents = {
        "runtime-requirements.txt": b"# empty runtime graph\n",
        "runtime-constraints.txt": b"# empty constraints\n",
        "install_release.py": b"helper\n",
        "install-linux-macos.sh": b'BOOTSTRAP_TAG="v1.2.3"\nBOOTSTRAP_HELPER_SHA256="'
        + hashlib.sha256(b"helper\n").hexdigest().encode()
        + b'"\n',
    }
    manifest["runtime_lock"]["sha256"] = hashlib.sha256(
        contents["runtime-requirements.txt"]
    ).hexdigest()
    manifest["runtime_constraints"]["sha256"] = hashlib.sha256(
        contents["runtime-constraints.txt"]
    ).hexdigest()
    (release / "release-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    contents["release-manifest.json"] = (release / "release-manifest.json").read_bytes()
    for filename, value in contents.items():
        (release / filename).write_bytes(value)
    (release / "install-linux-macos.sh").chmod(0o644)
    result = archive(release, tmp_path / "out")
    assert len(result) == 1
    with tarfile.open(result[0], "r:gz") as bundle:
        names = sorted(member.name for member in bundle.getmembers() if member.isfile())
        assert names == [
            f"app-1.2.3-linux-x86_64/{name}"
            for name in manifest["archive_members"]["linux-x86_64"]
        ]
        assert all(not name.endswith((".whl", ".pyc")) for name in names)
        shell_member = bundle.getmember("app-1.2.3-linux-x86_64/install-linux-macos.sh")
        assert shell_member.mode & 0o111


def test_archive_uses_common_downloads_and_canonical_windows_launcher(
    tmp_path, monkeypatch
) -> None:
    import hashlib
    import json
    import platform
    import zipfile

    import buildben_dev.packaging.installation_bundle as bundle

    release = tmp_path / "release"
    release.mkdir()
    manifest = _manifest()
    manifest["project"] = "buildben"
    manifest["version"] = "0.9.1"
    manifest["tag"] = "v0.9.1"
    manifest["platforms"] = {
        target: f"buildben-0.9.1-{target}.{suffix}"
        for target, suffix in bundle.TARGETS.items()
    }
    from buildben_dev.distribution.install_release import archive_members

    manifest["archive_members"] = {
        target: archive_members(target) for target in bundle.TARGETS
    }
    canonical = bundle._canonical_assets(bundle.ROOT, project="buildben")
    manifest["application_wheel"]["filename"] = "buildben-0.9.1-py3-none-any.whl"
    manifest["source_archive"]["filename"] = "buildben-0.9.1.tar.gz"
    contents = {
        "runtime-requirements.txt": b"# empty runtime graph\n",
        "runtime-constraints.txt": b"# empty constraints\n",
        "install_release.py": canonical["install_release.py"].read_bytes(),
    }
    manifest["runtime_lock"]["sha256"] = hashlib.sha256(
        contents["runtime-requirements.txt"]
    ).hexdigest()
    manifest["runtime_constraints"]["sha256"] = hashlib.sha256(
        contents["runtime-constraints.txt"]
    ).hexdigest()
    helper_digest = hashlib.sha256(contents["install_release.py"]).hexdigest()
    shell = canonical["install-linux-macos.sh"].read_text(encoding="utf-8")
    shell = shell.replace('BOOTSTRAP_TAG=""', 'BOOTSTRAP_TAG="v0.9.1"')
    shell = shell.replace(
        'BOOTSTRAP_HELPER_SHA256=""',
        f'BOOTSTRAP_HELPER_SHA256="{helper_digest}"',
    )
    powershell = canonical["install-windows.ps1"].read_text(encoding="utf-8")
    powershell = powershell.replace('$BootstrapTag = ""', '$BootstrapTag = "v0.9.1"')
    powershell = powershell.replace(
        '$BootstrapHelperSha256 = ""',
        f'$BootstrapHelperSha256 = "{helper_digest}"',
    )
    contents["install-linux-macos.sh"] = shell.encode("utf-8")
    contents["install-windows.ps1"] = powershell.encode("utf-8")
    for filename, data in contents.items():
        (release / filename).write_bytes(data)
    for filename in (
        "buildben-0.9.1-py3-none-any.whl",
        "buildben-0.9.1.tar.gz",
        "release-notes.md",
    ):
        (release / filename).write_bytes(b"common release asset\n")
    (release / "install-linux-macos.sh").chmod(0o644)
    manifest_path = release / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    archive_path = bundle.archive(release, tmp_path / "out")[0]
    with zipfile.ZipFile(archive_path) as archive_file:
        members = archive_file.namelist()
        assert any(name.endswith("/install-windows.cmd") for name in members)
        assert any(name.endswith("/install-windows.ps1") for name in members)
        assert any(name.endswith("/prepare-powershell-windows.cmd") for name in members)


def test_prepare_stages_prebuilt_assets_exports_and_deterministic_manifest(
    tmp_path, monkeypatch
) -> None:
    import hashlib
    import subprocess
    from types import SimpleNamespace

    from buildben_dev.packaging.installation_bundle import prepare

    root = tmp_path / "project"
    output = root / "dist"
    distribution = root / "src" / "demo_app_dev" / "distribution"
    distribution.mkdir(parents=True)
    output.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo_app"\nversion = "1.2.3"\nrequires-python = ">=3.12"\n',
        encoding="utf-8",
    )
    staged_notes = b"Precomputed release notes; preserve these exact bytes.\n"
    (output / "release-notes.md").write_bytes(staged_notes)
    (output / "demo_app-1.2.3-py3-none-any.whl").write_bytes(b"wheel")
    (output / "demo_app-1.2.3.tar.gz").write_bytes(b"sdist")
    template_root = (
        Path(__file__).resolve().parents[1] / "src" / "buildben" / "_templates_proj"
    )
    for template, name in (
        ("_src-dev-distribution-install-linux-macos.sh", "install-linux-macos.sh"),
        ("_src-dev-distribution-install-windows.ps1", "install-windows.ps1"),
        ("_src-dev-distribution-install-windows.cmd", "install-windows.cmd"),
        (
            "_src-dev-distribution-prepare-powershell-windows.cmd",
            "prepare-powershell-windows.cmd",
        ),
        ("_src-dev-distribution-install-macos.command", "install-macos.command"),
        ("_src-dev-distribution-install_release.py.tmpl", "install_release.py"),
    ):
        (distribution / name).write_bytes((template_root / template).read_bytes())

    calls = []

    def export(command, *, cwd, check, capture_output, text):
        calls.append(command)
        return SimpleNamespace(stdout="# locked empty runtime graph\n", stderr="")

    monkeypatch.setattr(subprocess, "run", export)
    manifest = prepare("owner/demo_app", "1" * 40, output, root=root, uv="uv")
    helper_digest = hashlib.sha256(
        (distribution / "install_release.py").read_bytes()
    ).hexdigest()
    assert len(calls) == 2
    assert calls[0][-1] == "requirements.txt"
    assert "--no-hashes" not in calls[0]
    assert calls[1].count("requirements.txt") == 1
    assert "--no-hashes" in calls[1]
    assert manifest["project"] == "demo_app"
    assert (
        manifest["application_wheel"]["filename"] == "demo_app-1.2.3-py3-none-any.whl"
    )
    assert manifest["archive_members"]["linux-x86_64"] == sorted(
        [
            "install-linux-macos.sh",
            "install_release.py",
            "release-manifest.json",
            "runtime-constraints.txt",
            "runtime-requirements.txt",
        ]
    )
    assert (
        output / "runtime-requirements.txt"
    ).read_bytes() == b"# locked empty runtime graph\n"
    shell = (output / "install-linux-macos.sh").read_text(encoding="utf-8")
    powershell = (output / "install-windows.ps1").read_text(encoding="utf-8")
    assert 'BOOTSTRAP_TAG="v1.2.3"' in shell
    assert f'BOOTSTRAP_HELPER_SHA256="{helper_digest}"' in shell
    assert '$BootstrapTag = "v1.2.3"' in powershell
    assert f'$BootstrapHelperSha256 = "{helper_digest}"' in powershell

    assert (output / "release-notes.md").read_bytes() == staged_notes
    before_missing_notes = {
        path.name: path.read_bytes()
        for path in output.iterdir()
        if path.is_file() and path.name != "release-notes.md"
    }
    (output / "release-notes.md").unlink()
    with pytest.raises(ValueError, match="Staged release notes"):
        prepare("owner/demo_app", "1" * 40, output, root=root, uv="uv")
    assert {
        path.name: path.read_bytes() for path in output.iterdir() if path.is_file()
    } == before_missing_notes
