"""Real AppRC-generated source-installer consumer tests."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import tomllib
import venv
from pathlib import Path, PurePosixPath

import pytest
from apprc.distribution import (
    PayloadTree,
    build_main_installer,
    install_support_files,
    read_project_metadata,
    render_bootstraps,
)
from apprc.distribution.models import DistributionSpec, ProjectMetadata
from apprc.distribution.standalone import MANAGEMENT_REQUIREMENTS
from buildben_distr.make_artifacts import distribution_spec
from buildben_dev.packaging import release_stage
from buildben_dev.packaging.release_stage import _locked_runtime_requirements
from support_source_transport.server import SourceFixture


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/HisQu/buildben.git"


def test_zipapp_release_staging_uses_generated_payload_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    generated_remote_consumer: Path,
) -> None:
    """Stage a real generated consumer using its authored zipapp specification."""

    source_root = generated_remote_consumer
    root = tmp_path / "zipapp-consumer"

    def ignore_generated(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".venv", "__pycache__", "release"}}

    shutil.copytree(source_root, root, ignore=ignore_generated)
    monkeypatch.syspath_prepend(str(root / "src"))
    original_spec = distribution_spec

    def zipapp_spec(project_root: Path, metadata: ProjectMetadata) -> DistributionSpec:
        return dataclasses.replace(
            original_spec(project_root, metadata),
            payload_format="zipapp",
        )

    monkeypatch.setattr(release_stage, "distribution_spec", zipapp_spec)
    monkeypatch.chdir(root)
    version = read_project_metadata(root).version
    commit = "b" * 40
    release_stage.stage_release(f"v{version}", commit, root=root)

    assets = root / "release" / "assets"
    names = {path.name for path in assets.iterdir()}
    assert "main-installer.pyz" in names
    assert "main-installer-requirements.txt" in names
    assert "main-installer.py" not in names
    manifest = json.loads((assets / "release-manifest.json").read_text("utf-8"))
    assert manifest["payload_format"] == "zipapp"
    assert manifest["commit"] == commit
    requirements = assets / "main-installer-requirements.txt"
    assert requirements.read_text(encoding="utf-8") == "".join(
        requirement + "\n" for requirement in MANAGEMENT_REQUIREMENTS
    )
    installer = assets / "app-install.sh"
    assert os.name == "nt" or installer.stat().st_mode & 0o111


def _main_installer(directory: Path, commit: str, project_root: Path = ROOT) -> Path:
    """Use AppRC's actual standalone generator for an immutable main identity."""
    metadata = read_project_metadata(project_root)
    spec = distribution_spec(project_root, metadata)
    spec = dataclasses.replace(
        spec,
        source_mode="main",
        release_commit=commit,
        runtime_requirements=tuple(
            dict.fromkeys(
                (
                    *spec.runtime_requirements,
                    *_locked_runtime_requirements(project_root),
                )
            )
        ),
    )
    modules = tuple(
        PurePosixPath("app_lifecycle") / filename
        for filename in ("__init__.py", "install.py", "uninstall.py", "actions.py")
    )
    source_payload = project_root / metadata.distribution_path / "payload"
    directory.mkdir(parents=True, exist_ok=True)
    payload_root = directory / "payload"
    shutil.copytree(source_payload, payload_root)
    base_payload = PayloadTree(payload_root, modules)
    for relative, content in install_support_files(spec, base_payload).items():
        resource = PurePosixPath("app_lifecycle/_support") / relative
        destination = payload_root.joinpath(*resource.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        if relative.name in {"launch.sh", "uninstall.sh"}:
            destination.chmod(0o700)
    support_root = payload_root / "app_lifecycle" / "_support"
    resources = tuple(
        PurePosixPath("app_lifecycle/_support", *path.relative_to(support_root).parts)
        for path in sorted(support_root.rglob("*"))
        if path.is_file()
    )
    artifact = build_main_installer(
        spec, PayloadTree(payload_root, modules, resources=resources)
    )
    installer = directory / "main-installer.py"
    installer.write_bytes(artifact.content)
    bootstrap_root = directory / "main-bootstrap"
    for bootstrap_artifact in render_bootstraps(spec):
        destination = bootstrap_root.joinpath(*bootstrap_artifact.destination.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(bootstrap_artifact.content)
        if bootstrap_artifact.executable:
            destination.chmod(0o700)
    return installer


@pytest.fixture(scope="module")
def generated_remote_consumer(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build an actual scaffolded AppRC application and stage its own packages."""
    import buildben.init_proj as scaffolder
    import tarfile

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
    metadata = read_project_metadata(root)
    result = _run(
        [
            sys.executable,
            "-m",
            f"{name}_dev.packaging.release_stage",
            f"v{metadata.version}",
            commit,
        ],
        cwd=root,
        environment=environment,
    )
    assert result.returncode == 0, result.stdout + result.stderr
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
                path, arcname=str(Path(f"{name}-{commit}") / relative), recursive=False
            )
    return root


def test_generated_app_source_install_smoke(generated_remote_consumer: Path) -> None:
    """Run the seeded generic native matrix for a real AppRC consumer."""
    root = generated_remote_consumer
    environment = os.environ.copy()
    environment["INSTALLER_SMOKE_MAIN_SOURCE"] = str(
        root.parent / "consumer-main.tar.gz"
    )
    environment["INSTALLER_SMOKE_MAIN_COMMIT"] = "a" * 40
    sdists = tuple((root / "dist").glob("*.tar.gz"))
    assert len(sdists) == 1
    environment["INSTALLER_SMOKE_SOURCE"] = str(sdists[0])
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
            "source_install_smoke or windows_installer_entries or official_uv_bootstrap",
        ],
        cwd=root,
        environment=environment,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _native_installation(environment: dict[str, str]) -> Path:
    app_id = "buildben"
    if os.name == "nt":
        root = Path(environment["LOCALAPPDATA"]) / app_id
    elif sys.platform == "darwin":
        root = Path(environment["HOME"]) / "Library" / "Application Support" / app_id
    else:
        root = Path(environment["XDG_DATA_HOME"]) / app_id
    return root / "installation"


def _install_environment(tmp_path: Path) -> dict[str, str]:
    """Isolate HOME/XDG/uv roots and preserve an active parent venv."""
    environment = os.environ.copy()
    for key, name in {
        "HOME": "home",
        "USERPROFILE": "home",
        "XDG_CONFIG_HOME": "config",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "XDG_CACHE_HOME": "cache",
        "LOCALAPPDATA": "local-appdata",
        "UV_CACHE_DIR": "uv-cache",
        "UV_TOOL_DIR": "uv-tools",
        "UV_TOOL_BIN_DIR": "uv-bin",
    }.items():
        path = tmp_path / name
        path.mkdir(exist_ok=True)
        environment[key] = str(path)
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("Source installer smoke requires the existing uv executable.")
    environment["APPRC_UV_PATH"] = str(Path(uv).resolve())
    parent_environment = tmp_path / "active parent environment"
    venv.EnvBuilder(with_pip=False).create(parent_environment)
    environment["VIRTUAL_ENV"] = str(parent_environment)
    scripts = parent_environment / ("Scripts" if os.name == "nt" else "bin")
    helper = tmp_path / "transport-client"
    helper.mkdir()
    for name in ("gh", "gh.py", "gh.cmd", "sitecustomize.py"):
        shutil.copy2(ROOT / "tests" / "support_source_transport" / name, helper / name)
    if os.name != "nt":
        (helper / "gh").chmod(0o700)
    environment["PYTHON"] = sys.executable
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(helper), environment.get("PYTHONPATH", ""))
    )
    environment["PATH"] = os.pathsep.join(
        (str(helper), str(scripts), environment.get("PATH", ""))
    )
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    environment["TMPDIR"] = str(temporary)
    environment["TEMP"] = str(temporary)
    environment["TMP"] = str(temporary)
    return environment


def _persistent_uv_without_initial_path(
    environment: dict[str, str], tmp_path: Path
) -> Path:
    """Select a real persistent uv while hiding uv and Python from initial PATH."""
    if os.name == "nt":
        raise ValueError("The restricted PATH fixture is POSIX-only.")
    uv_source = Path(environment.pop("APPRC_UV_PATH"))
    selected_uv = Path(environment["HOME"]) / ".local" / "bin" / "uv"
    selected_uv.parent.mkdir(parents=True)
    shutil.copy2(uv_source, selected_uv)
    environment["UV"] = str(selected_uv)
    minimal_bin = tmp_path / "minimal-bootstrap-bin"
    minimal_bin.mkdir()
    for command in (
        "basename",
        "cat",
        "dirname",
        "git",
        "mktemp",
        "pwd",
        "rm",
        "sed",
        "sh",
        "uname",
    ):
        executable = shutil.which(command)
        if executable is not None:
            (minimal_bin / command).symlink_to(executable)
    helper = tmp_path / "transport-client"
    environment["PATH"] = os.pathsep.join((str(helper), str(minimal_bin)))
    assert shutil.which("uv", path=environment["PATH"]) is None
    assert shutil.which("python", path=environment["PATH"]) is None
    assert shutil.which("python3", path=environment["PATH"]) is None
    return selected_uv


def _run(
    command: list[str], *, cwd: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize("source_mode", ["release", "main"])
@pytest.mark.parametrize("symlink_parent", [False, True])
@pytest.mark.parametrize("initial_path", ["normal", "restricted"])
def test_source_install_smoke(
    tmp_path: Path,
    source_mode: str,
    symlink_parent: bool,
    initial_path: str,
) -> None:
    """Install real source through rendered entries and selected bootstrap paths."""
    source_value = os.environ.get("INSTALLER_SMOKE_SOURCE")
    main_value = os.environ.get("INSTALLER_SMOKE_MAIN_SOURCE")
    commit = os.environ.get("INSTALLER_SMOKE_MAIN_COMMIT")
    client = os.environ.get("INSTALLER_SMOKE_CLIENT", "curl")
    if not source_value or not main_value or not commit:
        pytest.skip("Run just release-install-smoke to supply immutable source inputs.")
    if client not in {"curl", "gh"}:
        pytest.fail("INSTALLER_SMOKE_CLIENT must be curl or gh.")
    if symlink_parent and os.name == "nt":
        pytest.skip("Windows symlink creation requires privileges outside this test.")
    if initial_path == "restricted" and os.name == "nt":
        pytest.skip("The restricted executable PATH scenario is POSIX-only.")
    source = Path(source_value).resolve(strict=True)
    main_source = Path(main_value).resolve(strict=True)
    if len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        pytest.fail(
            "INSTALLER_SMOKE_MAIN_COMMIT must be a full lowercase SHA-1 commit."
        )
    main_archive = main_source
    release_assets = ROOT / "release" / "assets"
    if not release_assets.is_dir():
        pytest.fail("Run just release-install-smoke to stage authentic release assets.")
    staged_sdist = release_assets / source.name
    if not staged_sdist.is_file() or staged_sdist.read_bytes() != source.read_bytes():
        pytest.fail("The loopback release must serve the requested staged sdist bytes.")
    project_root = ROOT
    main_installer = _main_installer(
        tmp_path / "server-main", commit, project_root=project_root
    )
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tag = f"v{project['project']['version']}"
    moving_commit = (
        ("0" if commit != "0" * 40 else "1") * 40 if source_mode == "main" else None
    )
    fixture = SourceFixture(
        assets_directory=release_assets,
        main_installer=main_installer,
        main_installer_path=(
            read_project_metadata(project_root).distribution_path.as_posix()
            + "/artifacts/installer/main-installer.py"
        ),
        main_archive=main_archive,
        repository=REPOSITORY,
        commit=commit,
        tag=tag,
        moving_commit=moving_commit,
        moving_archive=b"the moved branch must not replace the captured source",
    )
    acquisition_root = tmp_path
    if symlink_parent:
        acquisition_root = tmp_path.parent / f"{tmp_path.name}-alias"
        acquisition_root.symlink_to(tmp_path, target_is_directory=True)
    environment = _install_environment(tmp_path)
    # > Alias acquisition only; managed authority and backend homes stay physical.
    temporary = str(acquisition_root / "temporary")
    for name in ("TMPDIR", "TEMP", "TMP"):
        environment[name] = temporary
    selected_uv = (
        _persistent_uv_without_initial_path(environment, tmp_path)
        if initial_path == "restricted"
        else None
    )
    mapping = acquisition_root / "source-url-map.json"
    mapping.write_text(json.dumps(fixture.url_map), encoding="utf-8")
    environment["INSTALLER_SMOKE_URL_MAP"] = str(mapping)
    environment["INSTALLER_SMOKE_API_URL"] = fixture.api_url
    caller = tmp_path / "unrelated caller directory"
    caller.mkdir()
    if source_mode == "release":
        entrypoint_root = release_assets
    else:
        entrypoint_root = tmp_path / "server-main" / "main-bootstrap"
    if os.name == "nt":
        entrypoint = entrypoint_root / "app-install.cmd"
        command = ["cmd.exe", "/d", "/c", str(entrypoint)]
    else:
        entrypoint = entrypoint_root / "app-install.sh"
        command = [str(entrypoint)]
    assert entrypoint.is_file(), entrypoint
    if client == "gh":
        command.extend(["--github-client", "gh"])
    command.extend(["--layout", "native"])
    try:
        installed = _run(command, cwd=caller, environment=environment)
        assert installed.returncode == 0, installed.stdout + installed.stderr
    finally:
        fixture.close()
    if source_mode == "main":
        assert fixture.main_resolution_count == 1
        assert fixture.main_archive_requests == [commit]
    assert not tuple(Path(environment["TMPDIR"]).glob("apprc-source-*"))
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / (
        "buildben.exe" if os.name == "nt" else "buildben"
    )
    help_result = _run([str(executable), "--help"], cwd=caller, environment=environment)
    assert help_result.returncode == 0, help_result.stdout + help_result.stderr
    state = _native_installation(environment)
    installed_record = json.loads(
        (state / "installation.json").read_text(encoding="utf-8")
    )
    assert installed_record["status"] == "ready"
    assert installed_record["current"] is not None
    if selected_uv is not None:
        assert str(selected_uv) in json.dumps(installed_record["current"])
    if source_mode == "main":
        assert commit in json.dumps(installed_record["current"]["source"])
    retained = Path(environment["XDG_DATA_HOME"]) / "buildben" / "unowned.txt"
    retained.parent.mkdir(parents=True, exist_ok=True)
    retained.write_text("retain unknown data\n", encoding="utf-8")
    if os.name == "nt":
        remove = ["cmd.exe", "/d", "/c", str(state / "uninstall.cmd"), "--yes"]
    else:
        remove = [str(state / "uninstall.sh"), "--yes"]
    removed = _run(remove, cwd=caller, environment=environment)
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert (state / "installation.json").is_file()
    assert retained.read_text(encoding="utf-8") == "retain unknown data\n"
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert record["status"] == "removed-retained"
    assert record["current"] is None
    assert record["last_successful"] is not None
    assert record["placement"]["capabilities"] == []
    assert not (Path(environment["UV_TOOL_DIR"]) / "buildben").exists()
    support_paths = tuple(
        output["path"]
        for output in record["owned_outputs"]
        if output["kind"] == "support"
    )
    complete_command = (
        [
            "cmd.exe",
            "/d",
            "/c",
            str(state / "uninstall.cmd"),
            "--yes",
            "--complete",
        ]
        if os.name == "nt"
        else [str(state / "uninstall.sh"), "--yes", "--complete"]
    )
    completed = _run(complete_command, cwd=caller, environment=environment)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not (state / "installation.json").exists()
    assert not (
        state / ("uninstall.cmd" if os.name == "nt" else "uninstall.sh")
    ).exists()
    assert all(not (state / path).exists() for path in support_paths)
    assert retained.read_text(encoding="utf-8") == "retain unknown data\n"
    assert not executable.exists()


@pytest.mark.skipif(
    os.name != "nt", reason="This procedure runs only on native Windows."
)
@pytest.mark.parametrize("entrypoint", ["file", "downloaded_text"])
def test_windows_installer_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    """Run generated checkout PowerShell as a file and as downloaded text."""
    import buildben.init_proj as scaffolder

    name = "windows_consumer"
    destination = tmp_path / "consumer"
    destination.mkdir()
    monkeypatch.setattr(scaffolder.utils, "warn_dir_overwrite", lambda _path: None)
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
    environment = _install_environment(tmp_path)
    environment["PYTHONPATH"] = os.pathsep.join(
        (
            str(ROOT / "src"),
            str(root / "src"),
            environment.get("PYTHONPATH", ""),
        )
    )
    build = _run(
        [sys.executable, "-m", f"{name}_distr.make_artifacts"],
        cwd=root,
        environment=environment,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    check = _run(
        [sys.executable, "-m", f"{name}_distr.make_artifacts", "--check"],
        cwd=root,
        environment=environment,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    original_path = environment["PATH"]
    persistent_uv = Path(environment["LOCALAPPDATA"]) / "persistent uv" / "uv.exe"
    persistent_uv.parent.mkdir(parents=True)
    shutil.copy2(Path(environment.pop("APPRC_UV_PATH")), persistent_uv)
    environment["UV"] = str(persistent_uv)
    environment["PATH"] = os.pathsep.join(
        directory
        for directory in original_path.split(os.pathsep)
        if directory
        and all(
            shutil.which(command, path=directory) is None
            for command in (
                "uv",
                "uv.exe",
                "python",
                "python.exe",
                "python3",
                "python3.exe",
            )
        )
    )
    assert shutil.which("uv", path=environment["PATH"]) is None
    assert shutil.which("python", path=environment["PATH"]) is None
    assert shutil.which("python3", path=environment["PATH"]) is None
    powershell = shutil.which("powershell.exe", path=original_path)
    if powershell is None:
        pytest.skip("Native Windows PowerShell is unavailable.")
    artifacts = root / "src" / f"{name}_distr" / "artifacts" / "installer"
    bootstrap = artifacts / "bootstrap.ps1"
    assert bootstrap.is_file()
    caller = tmp_path / "unrelated caller directory"
    caller.mkdir()
    if entrypoint == "file":
        command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(bootstrap),
            "--layout",
            "native",
        ]
    else:
        driver = artifacts / "invoke-downloaded-bootstrap.ps1"
        driver.write_text(
            "$ErrorActionPreference = 'Stop'\n"
            "$contents = [System.IO.File]::ReadAllText("
            "(Join-Path $PSScriptRoot 'bootstrap.ps1'))\n"
            "& ([ScriptBlock]::Create($contents)) '--layout' 'native'\n"
            "exit $LASTEXITCODE\n",
            encoding="utf-8",
        )
        command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(driver),
        ]
    installed = _run(command, cwd=caller, environment=environment)
    assert installed.returncode == 0, installed.stdout + installed.stderr
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / f"{name}.exe"
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    app_id = metadata["tool"]["apprc"]["distribution"]["app-id"]
    state = Path(environment["LOCALAPPDATA"]) / app_id / "installation"
    installed_record = json.loads(
        (state / "installation.json").read_text(encoding="utf-8")
    )
    assert installed_record["current"] is not None
    assert str(persistent_uv) in json.dumps(installed_record["current"]["backend"])
    help_result = _run([str(executable), "--help"], cwd=caller, environment=environment)
    assert help_result.returncode == 0, help_result.stdout + help_result.stderr
    environment["PATH"] = original_path
    removed = _run(
        ["cmd.exe", "/d", "/c", str(state / "uninstall.cmd"), "--yes"],
        cwd=caller,
        environment=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert record["status"] == "removed-retained"
    assert record["current"] is None
