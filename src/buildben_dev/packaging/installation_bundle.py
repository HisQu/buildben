"""Prepare and assemble deterministic, lock-backed release installation payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

TARGETS = {"windows-x86_64": "zip", "linux-x86_64": "tar.gz", "macos-arm64": "tar.gz"}
BASE_MEMBERS = [
    "install_release.py",
    "release-manifest.json",
    "runtime-constraints.txt",
    "runtime-requirements.txt",
]
ROOT = Path(__file__).resolve().parents[3]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _distribution(root: Path) -> tuple[str, str, str]:
    with (root / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    name, version, python = (
        project["name"],
        project["version"],
        project["requires-python"],
    )
    if (
        not isinstance(name, str)
        or not isinstance(version, str)
        or not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version)
        or not isinstance(python, str)
        or not python
    ):
        raise ValueError(
            "pyproject.toml must define distribution name, semantic version, and requires-python"
        )
    return name, version, python


def _safe_basename(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", value)
        or value in {".", ".."}
    ):
        raise ValueError(f"Unsafe manifest filename: {value!r}")
    return value


def _safe_member(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
    ):
        raise ValueError(f"Unsafe archive member: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError(f"Unsafe archive member: {value!r}")
    return value


def _manifest_members(target: str, *, project: str) -> list[str]:
    # > PersoDB retains its established nested Windows and root launcher layout.
    if _normalize(project) == "persodb":
        return _persodb_members(target)
    from ..distribution.install_release import archive_members

    return archive_members(target)


def _persodb_members(target: str) -> list[str]:
    files = [*BASE_MEMBERS]
    if target == "windows-x86_64":
        files.extend(
            (
                "launch-windows.cmd",
                "windows-internal/install-windows.ps1",
                "windows-internal/launch-windows.ps1",
                "windows-internal/prepare-powershell-windows.cmd",
            )
        )
    else:
        files.append("launch-linux-macos.sh")
    return sorted(files)


def _safe_export(data: str, *, constraints: bool = False) -> bytes:
    if not isinstance(data, str) or not data.strip():
        raise ValueError("uv export produced an empty runtime dependency file")
    lines: list[str] = []
    for line in data.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(line)
            continue
        if re.search(r"(?i)https?://[^\s/@:]+:[^\s/@]+@", stripped):
            raise ValueError("Runtime exports must not contain credential-bearing URLs")
        if re.search(
            r"(?i)(?:^|\s)(?:-e\s+)?(?:file:|editable\s*=|path\s*=|/home/|/Users/|[A-Z]:\\)",
            stripped,
        ):
            raise ValueError(
                "Runtime exports must not contain local/editable dependencies"
            )
        if constraints:
            match = re.match(r"^([A-Za-z0-9_.-]+)\[[^]\n]+\](?=[<=>!~@;\s])", line)
            if match:
                line = line[: match.start(0)] + match.group(1) + line[match.end(0) :]
        lines.append(line)
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def validate_manifest(manifest: Any, repository: str, commit: str) -> dict[str, Any]:
    """Validate release manifest fields, identity, and exact archive inventories."""
    keys = {
        "schema_version",
        "project",
        "version",
        "tag",
        "repository",
        "commit_sha",
        "python_requires",
        "application_wheel",
        "source_archive",
        "runtime_lock",
        "runtime_constraints",
        "platforms",
        "archive_members",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != keys
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
    ):
        raise ValueError("Unsupported or malformed release manifest")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
        or not re.fullmatch(r"[0-9a-f]{40}", commit)
        or manifest.get("repository") != repository
        or manifest.get("commit_sha") != commit
    ):
        raise ValueError(
            "Release manifest source identity does not match the requested source"
        )
    project, version = manifest.get("project"), manifest.get("version")
    if (
        not isinstance(project, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", project)
        or not isinstance(version, str)
        or not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version)
        or manifest.get("tag") != f"v{version}"
    ):
        raise ValueError("Malformed or inconsistent release project/tag/version")
    if (
        not isinstance(manifest.get("python_requires"), str)
        or not manifest["python_requires"]
    ):
        raise ValueError("Release manifest Python requirement is missing")
    for field in (
        "application_wheel",
        "source_archive",
        "runtime_lock",
        "runtime_constraints",
    ):
        entry = manifest[field]
        if (
            not isinstance(entry, dict)
            or set(entry) != {"filename", "sha256"}
            or not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", ""))
        ):
            raise ValueError(f"Malformed {field} manifest entry")
        _safe_basename(entry["filename"])
    wheel = manifest["application_wheel"]["filename"]
    parts = wheel.removesuffix(".whl").split("-")
    if (
        not wheel.endswith(".whl")
        or len(parts) not in (5, 6)
        or _normalize(parts[0]) != _normalize(project)
        or parts[1] != version
    ):
        raise ValueError("Application wheel does not match project/version")
    sdist = manifest["source_archive"]["filename"]
    if not sdist.endswith(f"-{version}.tar.gz") or _normalize(
        sdist[: -len(f"-{version}.tar.gz")]
    ) != _normalize(project):
        raise ValueError("Source archive does not match project/version")
    if (
        manifest["runtime_lock"]["filename"] != "runtime-requirements.txt"
        or manifest["runtime_constraints"]["filename"] != "runtime-constraints.txt"
    ):
        raise ValueError("Release manifest runtime filenames are inconsistent")
    platforms, members = manifest["platforms"], manifest["archive_members"]
    if (
        not isinstance(platforms, dict)
        or set(platforms) != set(TARGETS)
        or not isinstance(members, dict)
        or set(members) != set(TARGETS)
    ):
        raise ValueError("Release manifest has an invalid platform/member set")
    for target, suffix in TARGETS.items():
        if platforms[target] != f"{project}-{version}-{target}.{suffix}" or members[
            target
        ] != _manifest_members(target, project=project):
            raise ValueError(f"Unsafe or inconsistent archive contract for {target}")
        for member in members[target]:
            _safe_member(member)
    return manifest


def _wheel_matches(path: Path, name: str, version: str) -> bool:
    parts = path.name.removesuffix(".whl").split("-")
    return (
        path.name.endswith(".whl")
        and len(parts) in (5, 6)
        and _normalize(parts[0]) == _normalize(name)
        and parts[1] == version
    )


def _sdist_matches(path: Path, name: str, version: str) -> bool:
    suffix = f"-{version}.tar.gz"
    return path.name.endswith(suffix) and _normalize(
        path.name[: -len(suffix)]
    ) == _normalize(name)


def _canonical_assets(root: Path, *, project: str) -> dict[str, Path]:
    dev_package = _normalize(project).replace("-", "_") + "_dev"
    distribution = root / "src" / dev_package / "distribution"
    candidates = {
        "install-linux-macos.sh": distribution / "install-linux-macos.sh",
        "install-windows.ps1": distribution / "install-windows.ps1",
        "install_release.py": distribution / "install_release.py",
        "install-windows.cmd": distribution / "install-windows.cmd",
        "prepare-powershell-windows.cmd": distribution
        / "prepare-powershell-windows.cmd",
        "install-macos.command": distribution / "install-macos.command",
    }
    missing = [
        str(path)
        for path in candidates.values()
        if not path.is_file() or path.is_symlink()
    ]
    if missing:
        raise ValueError(
            "Required canonical installer asset is missing: " + ", ".join(missing)
        )
    return candidates


def prepare(
    repository: str, commit: str, output: Path, *, root: Path = ROOT, uv: str = "uv"
) -> dict[str, Any]:
    """Prepare lock exports and common release assets from prebuilt distributions.

    :param repository: OWNER/REPO of the immutable release source.
    :param commit: Full checked source commit SHA.
    :param output: Directory containing the existing wheel and sdist.
    :param root: Project root used for metadata and canonical installers.
    :param uv: uv executable used only for locked exports.
    :return: The deterministic release manifest.
    """
    if not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository
    ) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError(
            "--repository must be OWNER/REPO and --commit a full lowercase Git SHA"
        )
    if not output.is_dir():
        raise ValueError(f"Release directory does not exist: {output}")
    name, version, requires = _distribution(root)
    named_wheels = [
        path
        for path in output.glob("*.whl")
        if _normalize(path.name.split("-", 1)[0]) == _normalize(name)
    ]
    named_sdists = [
        path
        for path in output.glob("*.tar.gz")
        if path.name.lower().replace("_", "-").startswith(_normalize(name) + "-")
    ]
    if any(not _wheel_matches(path, name, version) for path in named_wheels) or any(
        not _sdist_matches(path, name, version) for path in named_sdists
    ):
        raise ValueError(
            f"Release directory contains a mixed-version {name} wheel or sdist"
        )
    wheels = sorted(named_wheels)
    sdists = sorted(named_sdists)
    if (
        len(wheels) != 1
        or len(sdists) != 1
        or wheels[0].is_symlink()
        or sdists[0].is_symlink()
    ):
        raise ValueError(
            f"Expected exactly one safe {name} {version} wheel and sdist in {output}"
        )
    assets = _canonical_assets(root, project=name)
    exports: dict[str, bytes] = {}
    for filename, extra in (
        ("runtime-requirements.txt", []),
        ("runtime-constraints.txt", ["--no-hashes"]),
    ):
        command = [
            uv,
            "export",
            "--locked",
            "--no-dev",
            "--no-default-groups",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            *extra,
        ]
        result = subprocess.run(
            command, cwd=root, check=True, capture_output=True, text=True
        )
        exports[filename] = _safe_export(
            result.stdout, constraints=filename == "runtime-constraints.txt"
        )
    staged = dict(exports)
    for filename, path in assets.items():
        staged[filename] = path.read_bytes()
    helper_digest = _sha256_bytes(staged["install_release.py"])
    for filename, tag_marker, hash_marker in (
        ("install-linux-macos.sh", 'BOOTSTRAP_TAG=""', 'BOOTSTRAP_HELPER_SHA256=""'),
        ("install-windows.ps1", '$BootstrapTag = ""', '$BootstrapHelperSha256 = ""'),
    ):
        text = staged[filename].decode("utf-8")
        if text.count(tag_marker) != 1 or text.count(hash_marker) != 1:
            raise ValueError(
                f"Canonical {filename} must contain exactly one unfilled bootstrap tag and helper digest"
            )
        text = text.replace(
            tag_marker, tag_marker.replace('""', f'"v{version}"')
        ).replace(hash_marker, hash_marker.replace('""', f'"{helper_digest}"'))
        staged[filename] = text.encode("utf-8")
    platforms = {
        target: f"{name}-{version}-{target}.{suffix}"
        for target, suffix in TARGETS.items()
    }
    members = {target: _manifest_members(target, project=name) for target in TARGETS}
    manifest = {
        "schema_version": 1,
        "project": name,
        "version": version,
        "tag": f"v{version}",
        "repository": repository,
        "commit_sha": commit,
        "python_requires": requires,
        "application_wheel": {
            "filename": wheels[0].name,
            "sha256": _sha256_file(wheels[0]),
        },
        "source_archive": {
            "filename": sdists[0].name,
            "sha256": _sha256_file(sdists[0]),
        },
        "runtime_lock": {
            "filename": "runtime-requirements.txt",
            "sha256": _sha256_bytes(exports["runtime-requirements.txt"]),
        },
        "runtime_constraints": {
            "filename": "runtime-constraints.txt",
            "sha256": _sha256_bytes(exports["runtime-constraints.txt"]),
        },
        "platforms": platforms,
        "archive_members": members,
    }
    validate_manifest(manifest, repository, commit)
    notes_path = output / "release-notes.md"
    if notes_path.is_symlink() or not notes_path.is_file():
        raise ValueError(
            "Staged release notes are missing or unsafe: dist/release-notes.md"
        )
    notes = notes_path.read_bytes()
    if not notes.strip():
        raise ValueError("Staged release notes are empty")
    staged["release-notes.md"] = notes
    staged["release-manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    # > Every output is validated and buffered before any release asset is replaced.
    for filename, data in staged.items():
        _safe_basename(filename)
        if not isinstance(data, bytes):
            raise ValueError(f"Invalid prepared asset: {filename}")
    for filename, data in staged.items():
        destination = output / filename
        temporary = output / f".{filename}.tmp"
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    return manifest


def _target_platform() -> str:
    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "windows-x86_64"
    if system == "Linux" and machine in {"amd64", "x86_64"}:
        return "linux-x86_64"
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    raise ValueError(f"Unsupported installation archive target: {system}/{machine}")


def _payload_bytes(
    release: Path, manifest: dict[str, Any], target: str
) -> dict[str, tuple[bytes, int]]:
    files = manifest["archive_members"][target]
    expected_names = set(files)
    content: dict[str, tuple[bytes, int]] = {}
    for member in files:
        path = release
        for part in PurePosixPath(member).parts:
            path = path / part
            if path.is_symlink():
                raise ValueError(f"Archive input is missing or unsafe: {member}")
        if not path.is_file():
            raise ValueError(f"Archive input is missing or unsafe: {member}")
        mode = stat.S_IMODE(path.stat().st_mode)
        content[member] = (path.read_bytes(), mode)
    for field in ("runtime_lock", "runtime_constraints"):
        entry = manifest[field]
        data, _ = content[entry["filename"]]
        if _sha256_bytes(data) != entry["sha256"]:
            raise ValueError(f"Missing or corrupt payload asset: {entry['filename']}")
    manifest_data, _ = content["release-manifest.json"]
    if json.loads(manifest_data) != manifest:
        raise ValueError("Archive manifest bytes are inconsistent")
    helper_data, _ = content["install_release.py"]
    helper_digest = _sha256_bytes(helper_data)
    for filename, tag_marker, digest_marker in (
        (
            "install-linux-macos.sh",
            f'BOOTSTRAP_TAG="{manifest["tag"]}"',
            f'BOOTSTRAP_HELPER_SHA256="{helper_digest}"',
        ),
        (
            "install-windows.ps1",
            f'$BootstrapTag = "{manifest["tag"]}"',
            f'$BootstrapHelperSha256 = "{helper_digest}"',
        ),
    ):
        if filename in expected_names:
            data, _ = content[filename]
            text = data.decode("utf-8")
            if text.count(tag_marker) != 1 or text.count(digest_marker) != 1:
                raise ValueError(
                    f"Stamped {filename} does not match its release helper and tag"
                )
    return content


def archive(release: Path, output: Path) -> list[Path]:
    """Build exactly one safe thin archive for the current supported platform."""
    manifest_path = release / "release-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Prepared payload is missing a safe release-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(
        manifest, manifest.get("repository", ""), manifest.get("commit_sha", "")
    )
    target = _target_platform()
    payload = _payload_bytes(release, manifest, target)
    root_name = f"{manifest['project']}-{manifest['version']}-{target}"
    destination = output / manifest["platforms"][target]
    output.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        if TARGETS[target] == "zip":
            with zipfile.ZipFile(
                temporary, "w", compression=zipfile.ZIP_DEFLATED
            ) as bundle:
                for member, (data, mode) in payload.items():
                    info = zipfile.ZipInfo(f"{root_name}/{member}")
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = (stat.S_IFREG | mode) << 16
                    bundle.writestr(info, data)
        else:
            with tarfile.open(temporary, "w:gz") as bundle:
                for member, (data, mode) in payload.items():
                    info = tarfile.TarInfo(f"{root_name}/{member}")
                    info.size, info.mode, info.uid, info.gid = len(data), mode, 0, 0
                    info.uname = info.gname = ""
                    import io

                    bundle.addfile(info, io.BytesIO(data))
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return [destination]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse prepare/archive commands without an architecture override."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--repository", required=True)
    prepare_parser.add_argument("--commit", required=True)
    prepare_parser.add_argument("--output-directory", type=Path, required=True)
    archive_parser = commands.add_parser("archive")
    archive_parser.add_argument("--release-directory", type=Path, required=True)
    archive_parser.add_argument("--output-directory", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one builder command with an actionable input error."""
    args = parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args.repository, args.commit, args.output_directory)
        else:
            archive(args.release_directory, args.output_directory)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        raise SystemExit(f"release payload error: {error}") from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
