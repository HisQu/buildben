"""Generated Python-entry and opt-in native release consumer coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import tomllib
import zipfile
from pathlib import Path

import pytest
from support_native_release import (
    disk_bytes,
    pin_fixture_sdk,
    sdk_authoring_environment,
)


def _assert_windows_console_pe(path: Path) -> None:
    """Check a cross-compiled Windows executable's PE64 AMD64 console header."""
    content = path.read_bytes()
    assert content[:2] == b"MZ"
    pe_offset = struct.unpack_from("<I", content, 0x3C)[0]
    assert content[pe_offset : pe_offset + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", content, pe_offset + 4)[0] == 0x8664
    optional_header = pe_offset + 24
    assert struct.unpack_from("<H", content, optional_header)[0] == 0x20B
    assert struct.unpack_from("<H", content, optional_header + 68)[0] == 3


def _run(
    command: list[str], *, cwd: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run one generated-project command and retain its diagnostics."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture(scope="session")
def native_generated_consumer(
    tmp_path_factory: pytest.TempPathFactory,
    request: pytest.FixtureRequest,
) -> tuple[str, Path, Path]:
    """Generate and genuinely release-build the current native consumer template."""
    if os.environ.get("APPRC_TEST_PYAPP") != "1":
        pytest.skip("Set APPRC_TEST_PYAPP=1 to build native generated consumers.")
    if hasattr(request.config, "workerinput"):
        pytest.fail("Run the opt-in native release canary serially with pytest -n 0.")
    if not sys.platform.startswith("linux"):
        pytest.skip("Native generated consumer execution is Linux-only.")
    import buildben.init_proj as scaffolder

    destination = tmp_path_factory.mktemp("generated-native-release")
    name = "native_consumer"

    scaffolder._run(
        argparse.Namespace(
            name=name,
            target_dir=str(destination),
            git_init=False,
            github_user="fixture-owner",
            frontend=None,
        )
    )
    root = destination / name
    environment, sdk_revision, sdk_version = sdk_authoring_environment(root)

    pin_fixture_sdk(root, sdk_revision)
    repository_source = Path(__file__).resolve().parents[1] / "src"
    sdk_source = os.environ.get("APPRC_TEST_SDK_SOURCE")
    environment["PYTHONPATH"] = os.pathsep.join(
        item
        for item in (
            str(Path(sdk_source).resolve() / "src") if sdk_source else "",
            str(root / "src"),
            str(repository_source),
        )
        if item
    )
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip(
            "The native generated consumer requires the existing uv executable."
        )
    environment["UV"] = str(Path(uv).resolve())
    for command in (
        [sys.executable, "-m", f"{name}_distr.make_artifacts"],
        [sys.executable, "-m", f"{name}_distr.make_artifacts", "--check"],
        ["uv", "lock"],
        ["uv", "build", "--wheel", "--sdist", "--out-dir", str(root / "dist")],
        ["git", "init", "--initial-branch=main"],
        ["git", "config", "user.name", "AppRC generated native test"],
        ["git", "config", "user.email", "apprc-native-test@example.invalid"],
        ["git", "config", "commit.gpgsign", "false"],
        ["git", "add", "--all"],
        ["git", "commit", "-m", "Generated native release fixture"],
    ):
        result = _run(command, cwd=root, environment=environment)
        assert result.returncode == 0, result.stdout + result.stderr
    commit_result = _run(
        ["git", "rev-parse", "HEAD"], cwd=root, environment=environment
    )
    assert commit_result.returncode == 0, commit_result.stderr
    commit = commit_result.stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    staged = _run(
        [
            sys.executable,
            "-m",
            f"{name}_dev.packaging.release_stage",
            f"v{version}",
            commit,
            "--repository",
            f"fixture-owner/{name}",
            "--extra",
            "gui",
        ],
        cwd=root,
        environment=environment,
    )
    assert staged.returncode == 0, staged.stdout + staged.stderr
    assets = root / "release" / "assets"
    native_names = (
        f"{name}-install-linux-x86_64",
        f"{name}-install-windows-x86_64.exe",
        f"{name}-launch-linux-x86_64",
        f"{name}-launch-windows-x86_64.exe",
    )
    for filename in (native_names[1], native_names[3]):
        _assert_windows_console_pe(assets / filename)
    manifest = json.loads(
        (assets / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["commit"] == commit
    assert manifest["version"] == version
    recorded = {item["filename"]: item for item in manifest["assets"]}
    for filename in native_names:
        content = (assets / filename).read_bytes()
        assert recorded[filename]["sha256"] == hashlib.sha256(content).hexdigest()
        assert recorded[filename]["size"] == len(content)
    authored_assets = destination / "authored-assets"
    shutil.copytree(assets, authored_assets)
    package_evidence = {
        item["filename"]: {
            "path": str(authored_assets / item["filename"]),
            "bytes": item["size"],
            "sha256": item["sha256"],
        }
        for item in manifest["assets"]
        if item["filename"].endswith((".whl", ".tar.gz"))
    }
    evidence = {
        "consumer": name,
        "version": version,
        "commit": commit,
        "sdk_revision": sdk_revision,
        "sdk_version": sdk_version,
        "built_packages": package_evidence,
        "native_artifacts": {
            filename: {
                "path": str(authored_assets / filename),
                "bytes": (authored_assets / filename).stat().st_size,
                "sha256": hashlib.sha256(
                    (authored_assets / filename).read_bytes()
                ).hexdigest(),
            }
            for filename in native_names
        },
    }
    evidence_path = destination / "native-release-evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return sdk_version, evidence_path, authored_assets


@pytest.mark.parametrize("symlink_tmp", [False, True])
def test_generated_native_release_install_and_retained_repair(
    native_generated_consumer: tuple[str, Path, Path],
    tmp_path: Path,
    symlink_tmp: bool,
) -> None:
    """Exercise immutable native installation, repair authority, and full removal."""
    if symlink_tmp and os.name == "nt":
        pytest.skip("Temporary-directory symlink selection is POSIX-only.")
    sdk_version, evidence_path, authored_assets = native_generated_consumer
    name = "native_consumer"
    downloads = tmp_path / "recipient-downloads"
    shutil.copytree(authored_assets, downloads)
    installer = downloads / f"{name}-install-linux-x86_64"
    try:
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(
                (
                    "UV_",
                    "PYTHON",
                    "PYAPP_",
                    "PIP_",
                    "CONDA",
                    "VIRTUAL_ENV",
                    "GIT_",
                    "GH_",
                    "GITHUB_",
                    "APPRC_TEST_",
                )
            )
            and not any(
                marker in key.upper()
                for marker in ("TOKEN", "AUTH", "PASSWORD", "CREDENTIAL")
            )
            and key != "HISQU_GH_PAT"
        }
        for variable, folder in {
            "HOME": "home",
            "XDG_DATA_HOME": "data",
            "XDG_CONFIG_HOME": "config",
            "XDG_CACHE_HOME": "cache",
            "XDG_STATE_HOME": "state",
            "UV_TOOL_DIR": "tools",
            "UV_TOOL_BIN_DIR": "bin",
            "UV_CACHE_DIR": "uv-cache",
            "UV_PYTHON_INSTALL_DIR": "managed-python",
            "TMPDIR": "temporary",
        }.items():
            path = tmp_path / folder
            path.mkdir(exist_ok=True)
            environment[variable] = str(path)
        bootstrap_root = Path(environment["XDG_DATA_HOME"]) / "pyapp"
        environment["TMP"] = environment["TEMP"] = environment["TMPDIR"]
        if symlink_tmp:
            alias = tmp_path / "temporary-alias"
            alias.symlink_to(environment["TMPDIR"], target_is_directory=True)
            environment["TMPDIR"] = str(alias)
        path = tmp_path / "restricted-path"
        path.mkdir()
        for tool in (
            "sh",
            "basename",
            "dirname",
            "pwd",
            "uname",
            "cat",
            "mktemp",
            "rm",
            "sed",
        ):
            executable = shutil.which(tool)
            assert executable is not None
            (path / tool).symlink_to(executable)
        assert shutil.which("gh", path=str(path)) is None
        assert shutil.which("git", path=str(path)) is None
        assert shutil.which("python", path=str(path)) is None
        assert shutil.which("python3", path=str(path)) is None
        assert shutil.which("uv", path=str(path)) is None
        environment["PATH"] = str(path)
        caller = tmp_path / "unrelated-caller"
        caller.mkdir()
        from apprc.distribution.runtime.controllers import repair_saved
        from apprc.user_files.installation.discovery import (
            inspect_installation,
            installation_directory,
        )

        installation = installation_directory(name, environment=environment)
        result = _run(
            [
                str(installer),
                "--layout",
                "native",
            ],
            cwd=caller,
            environment=environment,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        inspection = inspect_installation(installation, app_id=name)
        assert inspection.record is not None and inspection.record.current is not None
        snapshot = inspection.record.current
        prefix = snapshot.prefix
        assert snapshot.source.kind == "wheel"
        assert snapshot.source.version == "0.1.0"
        assert snapshot.backend.executable.is_file()
        command = Path(environment["UV_TOOL_BIN_DIR"]) / name
        assert command.is_file()
        retained_archive = installation / "installer-payload.zip"
        assert retained_archive.is_file()
        launcher = installation / "launch"
        assert launcher.is_file()
        with zipfile.ZipFile(retained_archive) as bundle:
            sources = json.loads(bundle.read("sources.json"))
            inventory = json.loads(bundle.read("inventory.json"))
            root_wheel = next(
                item
                for item in inventory
                if item["name"].casefold().replace("_", "-") == name.replace("_", "-")
            )
            wheel_bytes = bundle.read(root_wheel["filename"])
        assert sources["origin"]["kind"] == "release-sdist"
        assert sources["origin"]["version"] == "0.1.0"
        assert sources["source"]["kind"] == "wheel"
        assert sources["source"]["digest"] == root_wheel["digest"]
        assert snapshot.source.digest == root_wheel["digest"]
        assert Path(snapshot.source.requirement).name == root_wheel["filename"]
        assert hashlib.sha256(wheel_bytes).hexdigest() == root_wheel["digest"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        sdist_name = next(
            filename
            for filename in evidence["built_packages"]
            if filename.endswith(".tar.gz")
        )
        assert (
            sources["origin"]["digest"]
            == evidence["built_packages"][sdist_name]["sha256"]
        )
        assert Path(sources["origin"]["requirement"]).name == sdist_name
        case_key = "symlink" if symlink_tmp else "physical"
        checkpoints = evidence.setdefault("installation_cases", {})
        checkpoints[case_key] = {
            "installed_prefix": str(prefix),
            "installed_program_bytes": disk_bytes(prefix),
            "retained_archive": {
                "path": str(retained_archive),
                "bytes": retained_archive.stat().st_size,
                "sha256": hashlib.sha256(retained_archive.read_bytes()).hexdigest(),
            },
            "source_wheel": {
                "filename": root_wheel["filename"],
                "bytes": len(wheel_bytes),
                "sha256": root_wheel["digest"],
            },
            "linux_launcher": {
                "path": str(launcher),
                "bytes": launcher.stat().st_size,
                "sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
            },
            "managed_python_bytes": disk_bytes(
                Path(environment["UV_PYTHON_INSTALL_DIR"])
            ),
            "bootstrap_bytes": disk_bytes(bootstrap_root),
            "distribution_record_digest": snapshot.distribution_record_digest,
            "source": {
                "kind": snapshot.source.kind,
                "requirement": snapshot.source.requirement,
                "digest": snapshot.source.digest,
                "backend": str(snapshot.backend.executable),
            },
        }
        launched = _run(
            [str(launcher), "--help"],
            cwd=caller,
            environment=environment,
        )
        assert launched.returncode == 0, launched.stdout + launched.stderr
        evidence_path.write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
        probe = _run(
            [
                str(snapshot.interpreter),
                "-I",
                str(Path(__file__).parent / "support_native_release.py"),
                name,
                sdk_version,
            ],
            cwd=caller,
            environment=environment,
        )
        assert probe.returncode == 0, probe.stdout + probe.stderr
        probe_data = json.loads(probe.stdout)
        assert probe_data["sdk_version"] == sdk_version
        managed_config = Path(probe_data["managed_config"])
        managed_secrets = Path(probe_data["managed_secrets"])
        assert managed_config.is_file()
        assert managed_secrets.is_file()
        launcher_bytes = launcher.read_bytes()
        launcher.write_bytes(launcher_bytes + b"\nmodified generated launcher\n")
        refusal = _run(
            [str(installer), "--repair", "--directory", str(installation)],
            cwd=caller,
            environment=environment,
        )
        assert refusal.returncode != 0
        assert (
            launcher.read_bytes() == launcher_bytes + b"\nmodified generated launcher\n"
        )
        launcher.write_bytes(launcher_bytes)
        original_archive = retained_archive.read_bytes()
        retained_archive.write_bytes(original_archive + b"\ntampered\n")
        refusal = _run(
            [str(installer), "--repair", "--directory", str(installation)],
            cwd=caller,
            environment=environment,
        )
        assert refusal.returncode != 0
        assert retained_archive.read_bytes() == original_archive + b"\ntampered\n"
        retained_archive.write_bytes(original_archive)
        failed_record = inspect_installation(installation, app_id=name).record
        assert failed_record is not None and failed_record.operation is not None
        assert failed_record.operation.kind == "repair"
        assert failed_record.operation.phase == "failed"
        assert failed_record.last_successful == snapshot
        assert failed_record.owned_outputs == inspection.record.owned_outputs
        assert failed_record.current is not None
        assert failed_record.current.source == snapshot.source
        assert failed_record.current.backend == snapshot.backend
        appdata = snapshot.placement.appdata_dir
        assert appdata is not None
        appdata.mkdir(parents=True, exist_ok=True)
        unmanaged_sentinel = appdata / "native-canary-unmanaged-sentinel.txt"
        unmanaged_sentinel.write_text(
            "leave this unregistered file alone\n", encoding="utf-8"
        )
        shutil.rmtree(downloads)
        launcher.unlink()
        repair = installation / "repair-installer.py"
        base_python = Path(
            json.loads((installation / "management.json").read_text())["base_python"]
        )
        assert repair.is_file()
        assert base_python.is_absolute()
        assert not base_python.is_relative_to(prefix)
        assert not base_python.is_relative_to(installation)
        assert not base_python.is_relative_to(bootstrap_root)
        repaired = _run(
            list(repair_saved(installation)),
            cwd=caller,
            environment=environment,
        )
        assert repaired.returncode == 0, repaired.stdout + repaired.stderr
        assert launcher.is_file()
        repaired_inspection = inspect_installation(installation, app_id=name)
        assert repaired_inspection.record is not None
        assert repaired_inspection.record.current is not None
        assert repaired_inspection.record.current.backend == snapshot.backend
        assert repaired_inspection.record.current.source == snapshot.source
        assert managed_config.is_file()
        assert managed_secrets.is_file()
        complete = _run(
            [
                str(base_python),
                "-I",
                str(installation / "management.py"),
                "uninstall",
                "--directory",
                str(installation),
                "--complete",
                "--category",
                "config",
                "--category",
                "appdata",
                "--forget-retained",
                "--yes",
            ],
            cwd=caller,
            environment=environment,
        )
        assert complete.returncode == 0, complete.stdout + complete.stderr
        deadline = time.monotonic() + 30
        while (
            installation.exists()
            or prefix.exists()
            or command.exists()
            or managed_config.exists()
            or managed_secrets.exists()
        ) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not installation.exists()
        assert not prefix.exists()
        assert not command.exists()
        assert not managed_config.exists()
        assert not managed_secrets.exists()
        assert unmanaged_sentinel.read_text(encoding="utf-8") == (
            "leave this unregistered file alone\n"
        )
        assert base_python.is_file()
        checkpoints[case_key]["uninstalled_checkpoint"] = {
            "installation_exists": installation.exists(),
            "program_prefix_exists": prefix.exists(),
            "managed_config_exists": managed_config.exists(),
            "managed_secrets_exists": managed_secrets.exists(),
            "unmanaged_sentinel_exists": unmanaged_sentinel.exists(),
            "base_python_path": str(base_python),
            "base_python_bytes": base_python.stat().st_size,
            "base_python_sha256": hashlib.sha256(base_python.read_bytes()).hexdigest(),
            "managed_python_bytes": disk_bytes(
                Path(environment["UV_PYTHON_INSTALL_DIR"])
            ),
            "bootstrap_bytes": disk_bytes(bootstrap_root),
        }
        evidence_path.write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        if downloads.exists():
            shutil.rmtree(downloads)


@pytest.fixture(scope="module")
def generated_remote_consumer(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate, lock, and package a consumer without invoking native authoring."""
    import buildben.init_proj as scaffolder

    destination = tmp_path_factory.mktemp("generated-remote-consumer")
    name = "remote_consumer"
    scaffolder._run(
        argparse.Namespace(
            name=name,
            target_dir=str(destination),
            git_init=False,
            github_user="fixture-owner",
            frontend=None,
        )
    )
    root = destination / name
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(root / "src"), environment.get("PYTHONPATH", ""))
    )
    for command in (
        [sys.executable, "-m", f"{name}_distr.make_artifacts"],
        [sys.executable, "-m", f"{name}_distr.make_artifacts", "--check"],
        ["uv", "lock"],
        ["uv", "build", "--out-dir", str(root / "dist")],
    ):
        result = _run(command, cwd=root, environment=environment)
        assert result.returncode == 0, result.stdout + result.stderr
    commit = "a" * 40
    archive = destination / "consumer-main.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(
                part in {".venv", "dist", "release", "__pycache__"}
                for part in relative.parts
            ):
                continue
            output.add(
                path,
                arcname=str(Path(f"{name}-{commit}") / relative),
                recursive=False,
            )
    return root


def test_generated_app_source_install_smoke(
    generated_remote_consumer: Path,
) -> None:
    """Exercise app-install.py from outside the generated editable checkout."""
    root = generated_remote_consumer
    environment = os.environ.copy()
    environment["INSTALLER_SMOKE_MAIN_SOURCE"] = str(
        root.parent / "consumer-main.tar.gz"
    )
    environment["INSTALLER_SMOKE_MAIN_COMMIT"] = "a" * 40
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(root / "src"), environment.get("PYTHONPATH", ""))
    )
    result = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-n",
            "0",
            "-q",
            "tests/test_remote_consumer_package.py",
            "-k",
            "source_install_smoke",
        ],
        cwd=root,
        environment=environment,
    )
    assert result.returncode == 0, result.stdout + result.stderr
