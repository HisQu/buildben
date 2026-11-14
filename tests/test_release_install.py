"""Real native setup consumers, complete workspaces and editable ownership."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from support_native_release import pin_fixture_sdk, sdk_authoring_environment


@dataclass(frozen=True, slots=True)
class NativeConsumer:
    """Retain authenticated fixture products after removing the author checkout."""

    assets: Path
    source_archive: Path
    evidence: Path
    sdk_version: str
    sdk_revision: str
    git_environment: dict[str, str]
    name: str = "native_consumer"


def _run(
    command: list[str], *, cwd: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run one real consumer command and retain its diagnostics."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _succeeded(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def _native_enabled(request: pytest.FixtureRequest) -> None:
    if os.environ.get("APPRC_TEST_PYAPP") != "1":
        pytest.skip("Set APPRC_TEST_PYAPP=1 for real native consumer tests.")
    if hasattr(request.config, "workerinput"):
        pytest.fail("Run native consumers serially with pytest -n 0.")
    if not sys.platform.startswith("linux"):
        pytest.skip("Native consumer execution is deferred outside Linux.")


def _assert_windows_console_pe(path: Path) -> None:
    """Inspect PE64 AMD64 console headers without executing Windows code."""
    content = path.read_bytes()
    assert content[:2] == b"MZ"
    offset = struct.unpack_from("<I", content, 0x3C)[0]
    assert content[offset : offset + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", content, offset + 4)[0] == 0x8664
    assert struct.unpack_from("<H", content, offset + 24)[0] == 0x20B
    assert struct.unpack_from("<H", content, offset + 24 + 68)[0] == 3


def _add_workspace(root: Path) -> None:
    """Customize the actual scaffold with selected and unselected uv members."""
    project = root / "pyproject.toml"
    content = project.read_text(encoding="utf-8")
    content = content.replace(
        "dependencies = [", 'dependencies = [\n    "workspace-support",', 1
    ).replace(
        "[project.optional-dependencies]",
        '[project.optional-dependencies]\nfixture = ["workspace-extra"]',
        1,
    )
    content += (
        '\n[tool.uv.workspace]\nmembers = ["packages/*"]\n'
        "\n[tool.uv.sources]\n"
        "workspace-support = { workspace = true }\n"
        "workspace-extra = { workspace = true }\n"
    )
    project.write_text(content, encoding="utf-8")
    for name in ("workspace_support", "workspace_extra", "workspace_unused"):
        member = root / "packages" / name
        package = member / "src" / name
        package.mkdir(parents=True)
        (member / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools>=68", "wheel"]\n'
            'build-backend = "setuptools.build_meta"\n'
            f'\n[project]\nname = "{name.replace("_", "-")}"\n'
            'version = "1.0.0"\nrequires-python = ">=3.12"\n'
            '\n[tool.setuptools.packages.find]\nwhere = ["src"]\n',
            encoding="utf-8",
        )
        (package / "__init__.py").write_text(
            '"""Installed locked workspace fixture."""\n', encoding="utf-8"
        )
        (package / "value.py").write_text(
            f'MESSAGE = "{name}: locked workspace runtime"\n', encoding="utf-8"
        )


def test_generated_react_python_packages_select_one_workspace_without_native_build(
    tmp_path: Path,
) -> None:
    """Build ordinary packages from private React source without native compilation."""
    import buildben.init_proj as scaffolder

    repository = Path(__file__).resolve().parents[1]
    scaffolder._run(
        argparse.Namespace(
            name="package_consumer",
            target_dir=str(tmp_path),
            git_init=False,
            github_user="fixture-owner",
            frontend="react",
        )
    )
    root = tmp_path / "package_consumer"
    environment, sdk_revision, _ = sdk_authoring_environment(root)
    pin_fixture_sdk(root, sdk_revision)
    _add_workspace(root)
    uv = shutil.which("uv")
    assert uv is not None, "The committed locked package fixture requires uv."
    environment["UV"] = str(Path(uv).resolve())
    sdk_source = os.environ.get("APPRC_TEST_SDK_SOURCE")
    environment["PYTHONPATH"] = os.pathsep.join(
        str(path)
        for path in (
            *([Path(sdk_source).resolve() / "src"] if sdk_source else []),
            root / "src",
            repository / "src",
        )
    )
    _succeeded(_run([uv, "lock"], cwd=root, environment=environment))
    for command in (
        ["git", "init", "--initial-branch=main"],
        ["git", "config", "user.name", "AppRC package test"],
        ["git", "config", "user.email", "apprc-package-test@example.invalid"],
        ["git", "config", "commit.gpgsign", "false"],
        ["git", "add", "--all"],
        ["git", "commit", "-m", "Generated React package consumer"],
    ):
        _succeeded(_run(command, cwd=root, environment=environment))

    committed_inputs = tuple(
        path
        for path in (
            root / "pyproject.toml",
            root / "uv.lock",
            root / "pylock.toml",
            root / "frontend" / "package.json",
            root / "frontend" / "bun.lock",
        )
        if path.is_file()
    )
    input_bytes = {path: path.read_bytes() for path in committed_inputs}
    output = tmp_path / "python-packages"
    built = _run(
        [
            uv,
            "run",
            "--project",
            str(root),
            "--locked",
            "--group",
            "dev",
            "--",
            "python",
            "-m",
            "package_consumer_distr.make_artifacts",
            "--python-packages",
            "--output",
            str(output),
        ],
        cwd=root,
        environment=environment,
    )
    _succeeded(built)
    files = sorted(path.name for path in output.iterdir())
    assert len(files) == 2
    wheel = next(output.glob("*.whl"))
    sdist = next(output.glob("*.tar.gz"))
    assert len(list(output.glob("workspace_*.whl"))) == 0
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "package_consumer/_web/index.html" in names
    assert any(name.startswith("package_consumer/_web/assets/") for name in names)
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
    assert any(name.endswith("src/package_consumer/_web/index.html") for name in names)
    assert {path: path.read_bytes() for path in committed_inputs} == input_bytes
    assert not (root / "src" / "package_consumer" / "_web").exists()
    assert not (root / "frontend" / "node_modules").exists()
    assert not (root / "frontend" / "dist").exists()
    if (root / "dist").exists():
        assert not tuple((root / "dist").glob("*setup-*"))


@pytest.fixture(scope="session")
def native_generated_consumer(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> NativeConsumer:
    """Build one actual React/workspace scaffold, or reuse its verified evidence."""
    _native_enabled(request)
    import buildben.init_proj as scaffolder
    from buildben_dev.packaging.release_manifest import validate_directory

    repository = Path(__file__).resolve().parents[1]
    template_revision = _run(
        ["git", "rev-parse", "HEAD"], cwd=repository, environment=os.environ.copy()
    )
    _succeeded(template_revision)
    source_revision = template_revision.stdout.strip()
    reuse = os.environ.get("APPRC_TEST_GENERATED_NATIVE_FIXTURE")
    if reuse:
        evidence_path = Path(reuse)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert evidence["template_revision"] == source_revision
        environment, sdk_revision, sdk_version = sdk_authoring_environment(repository)
        assert evidence["sdk_revision"] == sdk_revision
        assert evidence["sdk_version"] == sdk_version
        assets = Path(evidence["assets"])
        validate_directory(assets, app_id="native_consumer", exact=True)
        for name, digest in evidence["native_artifacts"].items():
            assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == digest
        source_archive = Path(evidence["source_archive"])
        assert (
            hashlib.sha256(source_archive.read_bytes()).hexdigest()
            == (evidence["source_archive_digest"])
        )
        return NativeConsumer(
            assets,
            source_archive,
            evidence_path,
            sdk_version,
            sdk_revision,
            {
                key: value
                for key, value in environment.items()
                if key.startswith("GIT_CONFIG_")
            },
        )

    destination = tmp_path_factory.mktemp("generated-native-release")
    scaffolder._run(
        argparse.Namespace(
            name="native_consumer",
            target_dir=str(destination),
            git_init=False,
            github_user="fixture-owner",
            frontend="react",
        )
    )
    root = destination / "native_consumer"
    environment, sdk_revision, sdk_version = sdk_authoring_environment(root)
    pin_fixture_sdk(root, sdk_revision)
    _add_workspace(root)
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("The real native consumer requires uv.")
    environment["UV"] = str(Path(uv).resolve())
    sdk_source = os.environ.get("APPRC_TEST_SDK_SOURCE")
    environment["PYTHONPATH"] = os.pathsep.join(
        str(path)
        for path in (
            *([Path(sdk_source).resolve() / "src"] if sdk_source else []),
            root / "src",
            repository / "src",
        )
    )
    for command in (
        [str(uv), "lock"],
        ["git", "init", "--initial-branch=main"],
        ["git", "config", "user.name", "AppRC generated native test"],
        ["git", "config", "user.email", "apprc-native-test@example.invalid"],
        ["git", "config", "commit.gpgsign", "false"],
        ["git", "add", "--all"],
        ["git", "commit", "-m", "Generated React workspace consumer"],
    ):
        _succeeded(_run(command, cwd=root, environment=environment))
    committed = _run(["git", "rev-parse", "HEAD"], cwd=root, environment=environment)
    _succeeded(committed)
    commit = committed.stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    source_archive = destination / "editable-source.tar"
    _succeeded(
        _run(
            ["git", "archive", "--format=tar", "--output", str(source_archive), commit],
            cwd=root,
            environment=environment,
        )
    )
    print(
        "Building native React/workspace fixture from its committed lock.", flush=True
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "native_consumer_dev.packaging.release_stage",
            "v0.1.0",
            commit,
            "--repository",
            "fixture-owner/native_consumer",
            "--extra",
            "fixture",
        ],
        cwd=root,
        env=environment,
        check=True,
    )
    names = validate_directory(root / "dist", app_id="native_consumer", exact=True)
    assets = destination / "authored-assets"
    shutil.copytree(root / "release" / "assets", assets)
    assert validate_directory(assets, app_id="native_consumer", exact=True) == names
    _assert_windows_console_pe(assets / "native_consumer-setup-windows-x86_64.exe")
    assert not (root / "frontend" / "node_modules").exists()
    assert not (root / "src" / "native_consumer" / "_web").exists()
    evidence_path = destination / "native-release-evidence.json"
    evidence = {
        "template_revision": source_revision,
        "commit": commit,
        "sdk_revision": sdk_revision,
        "sdk_version": sdk_version,
        "assets": str(assets),
        "source_archive": str(source_archive),
        "source_archive_digest": hashlib.sha256(
            source_archive.read_bytes()
        ).hexdigest(),
        "native_artifacts": {
            name: hashlib.sha256((assets / name).read_bytes()).hexdigest()
            for name in names
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    # > Managed proof must not be able to import the author checkout or frontend.
    shutil.rmtree(root)
    print(f"APPRC_TEST_GENERATED_NATIVE_FIXTURE={evidence_path}", flush=True)
    return NativeConsumer(
        assets,
        source_archive,
        evidence_path,
        sdk_version,
        sdk_revision,
        {
            key: value
            for key, value in environment.items()
            if key.startswith("GIT_CONFIG_")
        },
    )


def _recipient_environment(
    root: Path, *, symlink_tmp: bool, git_environment: dict[str, str]
) -> dict[str, str]:
    """Isolate all installation state while retaining explicit SDK fixture routing."""
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
                "BUN_",
            )
        )
        and not any(
            marker in key.upper()
            for marker in (
                "TOKEN",
                "AUTH",
                "PASSWORD",
                "CREDENTIAL",
            )
        )
        and key not in {"HISQU_GH_PAT", "UV", "BUN"}
    }
    environment.update(git_environment)
    for variable, folder in {
        "HOME": "home",
        "XDG_DATA_HOME": "data",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_STATE_HOME": "state",
        "UV_TOOL_BIN_DIR": "bin",
        "UV_CACHE_DIR": "uv-cache",
        "UV_PYTHON_INSTALL_DIR": "managed-python",
        "TMPDIR": "temporary",
    }.items():
        path = root / folder
        path.mkdir(exist_ok=True)
        environment[variable] = str(path)
    if symlink_tmp:
        alias = root / "temporary-alias"
        alias.symlink_to(environment["TMPDIR"], target_is_directory=True)
        environment["TMPDIR"] = str(alias)
    environment["TMP"] = environment["TEMP"] = environment["TMPDIR"]
    tools = root / "recipient-tools"
    tools.mkdir()
    for name in (
        "git",
        "sh",
        "basename",
        "dirname",
        "pwd",
        "uname",
        "cat",
        "mktemp",
        "rm",
        "sed",
        "tar",
        "gzip",
        "env",
        "readlink",
    ):
        executable = shutil.which(name)
        assert executable is not None
        (tools / name).symlink_to(executable)
    environment["PATH"] = os.pathsep.join(
        (
            environment["UV_TOOL_BIN_DIR"],
            str(tools),
        )
    )
    assert shutil.which("bun", path=environment["PATH"]) is None
    assert shutil.which("python", path=environment["PATH"]) is None
    return environment


def _runtime_environment(root: Path, environment: dict[str, str]) -> dict[str, str]:
    """Make recipient Bun, git and authoring Python unavailable to forwarded apps."""
    restricted = root / "runtime-path"
    restricted.mkdir()
    for tool in ("sh", "basename", "dirname", "pwd", "uname", "cat", "mktemp", "rm"):
        executable = shutil.which(tool)
        assert executable is not None
        (restricted / tool).symlink_to(executable)
    captured = environment | {
        "PATH": os.pathsep.join((environment["UV_TOOL_BIN_DIR"], str(restricted))),
        "VIRTUAL_ENV": str(root / "unrelated-active-environment"),
        "PYTHONPATH": str(root / "unrelated-python-imports"),
    }
    assert shutil.which("bun", path=captured["PATH"]) is None
    assert shutil.which("git", path=captured["PATH"]) is None
    return captured


def _assert_served_assets(
    command: Path, *, cwd: Path, environment: dict[str, str]
) -> None:
    """Fetch real installed HTML and its Vite JavaScript from the app's stdlib server."""
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            [str(command), "web", "--host", "127.0.0.1", "--port", "0"],
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            start_new_session=True,
        )
        assert process.stdout is not None
        try:
            readable, _, _ = select.select([process.stdout], [], [], 120)
            assert readable, "Installed static server did not announce its bound port."
            line = process.stdout.readline()
            match = re.search(r"http://127\.0\.0\.1:\d+/", line)
            assert match is not None, line
            url = match[0]
            with urllib.request.urlopen(url, timeout=15) as response:
                assert response.status == 200
                html = response.read()
            assert b'<div id="root">' in html
            scripts = re.findall(rb'src=["\']([^"\']+\.js)["\']', html)
            assert scripts, html
            with urllib.request.urlopen(
                url.rstrip("/") + "/" + scripts[0].decode().lstrip("/"), timeout=15
            ) as response:
                assert response.status == 200
                javascript = response.read()
            assert b"native_consumer" in javascript
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=30)


@pytest.mark.parametrize("symlink_tmp", [False, True])
def test_generated_native_release_install_and_retained_repair(
    native_generated_consumer: NativeConsumer, tmp_path: Path, symlink_tmp: bool
) -> None:
    """Install a locked hybrid, repair a broken slot and remove without app imports."""
    from apprc.definition.installation import RuntimeSlot
    from apprc.distribution.runtime.backend import runtime_interpreter
    from apprc.user_files.installation.discovery import (
        inspect_installation,
        installation_directory,
    )

    fixture = native_generated_consumer
    environment = _recipient_environment(
        tmp_path, symlink_tmp=symlink_tmp, git_environment=fixture.git_environment
    )
    caller = tmp_path / "unrelated-caller"
    caller.mkdir()
    downloads = tmp_path / "downloads"
    shutil.copytree(fixture.assets, downloads)
    setup = downloads / f"{fixture.name}-setup-linux-x86_64"
    print(
        f"Installing managed generated consumer (symlink_tmp={symlink_tmp}).",
        flush=True,
    )
    _succeeded(
        _run(
            [
                str(setup),
                "app",
                "install",
                "--yes",
                "--skip-setup",
                "--command-directory",
                environment["UV_TOOL_BIN_DIR"],
            ],
            cwd=caller,
            environment=environment,
        )
    )
    directory = installation_directory(fixture.name, environment=environment)
    inspection = inspect_installation(directory, app_id=fixture.name)
    record = inspection.record
    assert record is not None and record.status == "ready"
    slot = record.active_runtime
    assert isinstance(slot, RuntimeSlot)
    assert slot.version == "0.1.0" and slot.python_version is not None
    assert slot.selection.extras == ("fixture",)
    evidence = json.loads(fixture.evidence.read_text(encoding="utf-8"))
    assert slot.source.commit == evidence["commit"]
    slot_root = directory / "runtimes" / str(slot.slot_id)
    archive = slot_root / "project.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == slot.source.digest
    with zipfile.ZipFile(archive) as project:
        names = project.namelist()
        assert (
            hashlib.sha256(project.read("uv.lock")).hexdigest()
            == slot.source.lock_digest
        )
        for name in ("workspace_support", "workspace_extra", "workspace_unused"):
            assert f"packages/{name}/pyproject.toml" in names
        assert "src/native_consumer/_web/index.html" in names
        assert not any(
            part in {".venv", "node_modules", ".cache", "__pycache__"}
            for name in names
            for part in Path(name).parts
        )
        assert not any(name.startswith("frontend/dist/") for name in names)
    stable = directory / fixture.name
    command = Path(environment["UV_TOOL_BIN_DIR"]) / fixture.name
    assert stable.read_bytes() == setup.read_bytes()
    assert command.is_symlink() and command.resolve() == stable
    editable_refusal = _run(
        [str(stable), "app", "install", "-e", "--yes"],
        cwd=caller,
        environment=environment,
    )
    assert editable_refusal.returncode != 0
    assert "uv run --locked" in (editable_refusal.stdout + editable_refusal.stderr)
    interpreter = runtime_interpreter(directory, slot)
    installed = _run(
        [
            str(interpreter),
            "-I",
            "-c",
            "import importlib.util, importlib.metadata, json, sys; "
            "from importlib.resources import files; "
            "from workspace_support.value import MESSAGE; "
            "import workspace_extra; "
            "print(json.dumps({'prefix':sys.prefix,"
            "'sdk':importlib.metadata.version('apprc-core'),"
            "'html':files('native_consumer').joinpath('_web/index.html').read_text(),"
            "'workspace':MESSAGE,"
            "'unused':importlib.util.find_spec('workspace_unused') is not None,"
            "'dev':importlib.util.find_spec('jupyterlab') is not None}))",
        ],
        cwd=caller,
        environment=environment,
    )
    _succeeded(installed)
    payload = json.loads(installed.stdout)
    assert Path(payload["prefix"]) == slot_root / ".venv"
    assert payload["sdk"] == fixture.sdk_version
    assert '<div id="root">' in payload["html"]
    assert payload["workspace"] == "workspace_support: locked workspace runtime"
    assert payload["unused"] is False and payload["dev"] is False
    shutil.rmtree(slot_root / "source" / "frontend")
    runtime_environment = _runtime_environment(tmp_path, environment)
    _assert_served_assets(command, cwd=caller, environment=runtime_environment)
    _succeeded(
        _run(
            [str(command), "config", "setup", "--yes"],
            cwd=caller,
            environment=runtime_environment,
        )
    )
    _succeeded(
        _run(
            [
                str(command),
                "config",
                "set",
                "app.message",
                "retained across repair",
                "--scope",
                "user",
            ],
            cwd=caller,
            environment=runtime_environment,
        )
    )
    assert record.placement.appdata_dir is not None
    data = record.placement.appdata_dir / "unmanaged-sentinel.txt"
    data.write_bytes(b"retain unregistered application data\n")
    unknown = directory / "unknown-installation-file"
    unknown.write_bytes(b"never sweep installation children\n")
    print("Checking independent doctor and replacement-slot repair.", flush=True)
    shutil.rmtree(slot_root / ".venv")
    doctor = _run(
        [str(stable), "app", "doctor", "--json"], cwd=caller, environment=environment
    )
    assert doctor.returncode != 0
    diagnosis = json.loads(doctor.stdout)
    assert any(
        word in json.dumps(diagnosis).lower() for word in ("unavailable", "missing")
    )
    _succeeded(
        _run([str(stable), "app", "repair"], cwd=caller, environment=environment)
    )
    repaired = inspect_installation(directory, app_id=fixture.name)
    assert repaired.record is not None
    replacement = repaired.record.active_runtime
    assert isinstance(replacement, RuntimeSlot)
    assert replacement.slot_id != slot.slot_id
    assert replacement.source == slot.source
    assert repaired.record.placement == record.placement
    replacement_root = directory / "runtimes" / str(replacement.slot_id)
    shutil.rmtree(replacement_root / "source" / "frontend")
    _assert_served_assets(command, cwd=caller, environment=runtime_environment)
    retained_archive = replacement_root / "project.zip"
    original = retained_archive.read_bytes()
    retained_archive.write_bytes(original + b"tampered snapshot")
    refusal = _run([str(stable), "app", "repair"], cwd=caller, environment=environment)
    assert refusal.returncode != 0
    retained_archive.write_bytes(original)
    still_active = inspect_installation(directory, app_id=fixture.name).record
    assert still_active is not None and still_active.active_runtime == replacement
    shown = _run(
        [str(command), "config", "show", "--json"],
        cwd=caller,
        environment=runtime_environment,
    )
    _succeeded(shown)
    assert "retained across repair" in shown.stdout
    _succeeded(
        _run(
            [
                str(command),
                "config",
                "set",
                "app.message",
                "fresh writer after failure",
                "--scope",
                "user",
            ],
            cwd=caller,
            environment=runtime_environment,
        )
    )
    # > Program removal must remain independent even after the application breaks.
    shutil.rmtree(replacement_root / ".venv")
    print(
        "Removing broken managed program while retaining owned placement.", flush=True
    )
    _succeeded(
        _run(
            [str(stable), "app", "uninstall", "--yes"],
            cwd=caller,
            environment=environment,
        )
    )
    retained = inspect_installation(directory, app_id=fixture.name).record
    assert retained is not None and retained.status == "removed-retained"
    assert retained.active_runtime is None and retained.operation is None
    assert not os.path.lexists(command)
    assert data.read_bytes() == b"retain unregistered application data\n"
    assert unknown.read_bytes() == b"never sweep installation children\n"
    assert Path(environment["UV_CACHE_DIR"]).is_dir()
    assert Path(environment["UV_PYTHON_INSTALL_DIR"]).is_dir()


@pytest.mark.parametrize("symlink_tmp", [False, True])
def test_generated_native_release_install_editable_ownership(
    native_generated_consumer: NativeConsumer, tmp_path: Path, symlink_tmp: bool
) -> None:
    """Register the real generated checkout without claiming its source or venv."""
    from apprc.definition.installation import EditableCheckout, RuntimeSlot
    from apprc.user_files.installation.discovery import (
        inspect_installation,
        installation_directory,
    )

    fixture = native_generated_consumer
    environment = _recipient_environment(
        tmp_path, symlink_tmp=symlink_tmp, git_environment=fixture.git_environment
    )
    setup = fixture.assets / f"{fixture.name}-setup-linux-x86_64"
    _succeeded(
        _run(
            [
                str(setup),
                "app",
                "install",
                "--yes",
                "--skip-setup",
                "--command-directory",
                environment["UV_TOOL_BIN_DIR"],
            ],
            cwd=tmp_path,
            environment=environment,
        )
    )
    directory = installation_directory(fixture.name, environment=environment)
    managed = inspect_installation(directory, app_id=fixture.name).record
    assert managed is not None and isinstance(managed.active_runtime, RuntimeSlot)
    assert managed.placement.appdata_dir is not None
    retained_data = managed.placement.appdata_dir / "mode-switch-sentinel"
    retained_data.write_bytes(b"preserve resources across ownership modes\n")
    checkout = tmp_path / "developer checkout"
    checkout.mkdir()
    with tarfile.open(fixture.source_archive) as source:
        source.extractall(checkout, filter="data")
    uv = shutil.which("uv")
    assert uv is not None
    (tmp_path / "recipient-tools" / "uv").symlink_to(uv)
    environment["UV"] = uv
    _succeeded(
        _run(
            [uv, "sync", "--locked", "--no-default-groups", "--extra", "fixture"],
            cwd=checkout,
            environment=environment,
        )
    )
    environment["UV_NO_SYNC"] = "1"
    source_sentinel = checkout / "developer-file"
    environment_sentinel = checkout / ".venv" / "developer-file"
    source_sentinel.write_bytes(b"checkout stays developer-owned\n")
    environment_sentinel.write_bytes(b"venv stays developer-owned\n")
    before = (checkout / ".venv").stat()
    lock = (checkout / "uv.lock").read_bytes()
    command = checkout / ".venv" / "bin" / fixture.name
    for _ in range(2):
        _succeeded(
            _run(
                [
                    uv,
                    "run",
                    "--locked",
                    fixture.name,
                    "app",
                    "install",
                    "-e",
                    "--yes",
                    "--skip-setup",
                ],
                cwd=checkout,
                environment=environment,
            )
        )
    inspection = inspect_installation(directory, app_id=fixture.name)
    assert inspection.record is not None
    runtime = inspection.record.active_runtime
    assert isinstance(runtime, EditableCheckout)
    assert runtime.project == checkout.resolve()
    assert runtime.environment == (checkout / ".venv").resolve()
    assert not inspection.record.retiring_runtime_ids
    assert inspection.record.placement == managed.placement
    assert retained_data.read_bytes() == b"preserve resources across ownership modes\n"
    global_command = Path(environment["UV_TOOL_BIN_DIR"]) / fixture.name
    caller = tmp_path / "outside checkout"
    caller.mkdir()
    observed = _run(
        [str(global_command), "diagnose", "--json"], cwd=caller, environment=environment
    )
    _succeeded(observed)
    assert Path(json.loads(observed.stdout)["package_file"]).is_relative_to(checkout)
    _succeeded(
        _run(
            [
                str(setup),
                "app",
                "install",
                "--yes",
                "--skip-setup",
                "--command-directory",
                environment["UV_TOOL_BIN_DIR"],
            ],
            cwd=caller,
            environment=environment,
        )
    )
    switched_back = inspect_installation(directory, app_id=fixture.name).record
    assert switched_back is not None
    assert isinstance(switched_back.active_runtime, RuntimeSlot)
    assert switched_back.placement == managed.placement
    assert retained_data.read_bytes() == b"preserve resources across ownership modes\n"
    _succeeded(
        _run(
            [str(global_command), "app", "uninstall", "--yes"],
            cwd=caller,
            environment=environment,
        )
    )
    assert source_sentinel.read_bytes() == b"checkout stays developer-owned\n"
    assert environment_sentinel.read_bytes() == b"venv stays developer-owned\n"
    after = (checkout / ".venv").stat()
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    assert (checkout / "uv.lock").read_bytes() == lock
    assert command.is_file()
    assert not os.path.lexists(global_command)


@pytest.fixture(scope="session")
def native_buildben_assets(request: pytest.FixtureRequest) -> Path:
    """Build the canonical zero-data argparse consumer using its normal authoring CLI."""
    _native_enabled(request)
    from buildben_dev.packaging.release_manifest import validate_directory

    root = Path(__file__).resolve().parents[1]
    reuse = os.environ.get("APPRC_TEST_BUILDBEN_NATIVE_ASSETS")
    if reuse:
        assets = Path(reuse)
        validate_directory(assets, app_id="buildben", exact=False)
        return assets
    environment = os.environ.copy()
    sdk_source = environment.get("APPRC_TEST_SDK_SOURCE")
    environment["PYTHONPATH"] = os.pathsep.join(
        str(path)
        for path in (
            *([Path(sdk_source).resolve() / "src"] if sdk_source else []),
            root / "src",
        )
    )
    print("Building the canonical zero-data Buildben native setup.", flush=True)
    subprocess.run(
        [sys.executable, "-m", "buildben_distr.make_artifacts"],
        cwd=root,
        env=environment,
        check=True,
    )
    validate_directory(root / "dist", app_id="buildben", exact=False)
    return root / "dist"


@pytest.mark.parametrize("symlink_tmp", [False, True])
def test_canonical_native_release_install(
    native_buildben_assets: Path, tmp_path: Path, symlink_tmp: bool
) -> None:
    """Keep Buildben usable as argparse without installing AppRC into its runtime."""
    from apprc.definition.installation import RuntimeSlot
    from apprc.distribution.runtime.backend import runtime_interpreter
    from apprc.user_files.installation.discovery import (
        inspect_installation,
        installation_directory,
    )

    environment = _recipient_environment(
        tmp_path, symlink_tmp=symlink_tmp, git_environment={}
    )
    setup = native_buildben_assets / "buildben-setup-linux-x86_64"
    _succeeded(
        _run(
            [
                str(setup),
                "app",
                "install",
                "--yes",
                "--command-directory",
                environment["UV_TOOL_BIN_DIR"],
            ],
            cwd=tmp_path,
            environment=environment,
        )
    )
    directory = installation_directory("buildben", environment=environment)
    record = inspect_installation(directory, app_id="buildben").record
    assert record is not None and isinstance(record.active_runtime, RuntimeSlot)
    committed = _run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        environment=os.environ.copy(),
    )
    _succeeded(committed)
    assert record.active_runtime.source.commit == committed.stdout.strip()
    assert not record.placement.capabilities
    interpreter = runtime_interpreter(directory, record.active_runtime)
    dependency = _run(
        [
            str(interpreter),
            "-I",
            "-c",
            "import importlib.util; print(importlib.util.find_spec('apprc') is None)",
        ],
        cwd=tmp_path,
        environment=environment,
    )
    _succeeded(dependency)
    assert dependency.stdout.strip() == "True"
    command = Path(environment["UV_TOOL_BIN_DIR"]) / "bube"
    _succeeded(_run([str(command), "--help"], cwd=tmp_path, environment=environment))
    _succeeded(
        _run(
            [str(command), "app", "uninstall", "--yes"],
            cwd=tmp_path,
            environment=environment,
        )
    )
    retained = inspect_installation(directory, app_id="buildben").record
    assert retained is not None and retained.status == "removed-retained"
    assert retained.active_runtime is None
    assert not os.path.lexists(command)
