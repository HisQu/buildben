"""Real generated-consumer lifecycle smoke tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
import tomllib
import venv
from pathlib import Path
from typing import Iterator

import pytest


def _create_consumer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    name: str,
    custom_actions: bool = False,
) -> tuple[Path, dict[str, str], Path]:
    """Scaffold, author any consumer actions, and invoke real SDK generation."""
    import buildben.init_proj as scaffolder

    monkeypatch.setattr(scaffolder.utils, "warn_dir_overwrite", lambda _path: None)
    destination = tmp_path / "consumer space"
    destination.mkdir()
    scaffolder._run(
        argparse.Namespace(
            name=name,
            target_dir=str(destination),
            git_init=False,
            github_user="fixture-owner",
        )
    )
    root = destination / name
    environment = os.environ.copy()
    repository_source = Path(__file__).resolve().parents[1] / "src"
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(repository_source), str(root / "src"), environment.get("PYTHONPATH", ""))
    )
    for key, folder in {
        "HOME": "home",
        "USERPROFILE": "home",
        "XDG_STATE_HOME": "state",
        "XDG_DATA_HOME": "data",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "LOCALAPPDATA": "local data",
        "UV_TOOL_DIR": "tools",
        "UV_TOOL_BIN_DIR": "tool binaries",
        "UV_CACHE_DIR": "uv cache",
    }.items():
        path = tmp_path / f"{name}-{folder}"
        path.mkdir(exist_ok=True)
        environment[key] = str(path)
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("The real lifecycle smoke requires the existing uv executable.")
    environment["APPRC_UV_PATH"] = str(Path(uv).resolve())
    parent_environment = tmp_path / f"{name}-active-parent-venv"
    venv.EnvBuilder(with_pip=False).create(parent_environment)
    environment["VIRTUAL_ENV"] = str(parent_environment)
    scripts = parent_environment / ("Scripts" if os.name == "nt" else "bin")
    environment["PATH"] = os.pathsep.join((str(scripts), environment.get("PATH", "")))
    if custom_actions:
        environment["LIFECYCLE_CUSTOM_STATE"] = str(tmp_path / f"{name}-custom-state")
        environment["LIFECYCLE_CUSTOM_RESULT"] = str(
            tmp_path / f"{name}-cleanup-result"
        )
        environment["LIFECYCLE_CUSTOM_BIN"] = str(
            Path(environment["UV_TOOL_BIN_DIR"])
            / (name + (".exe" if os.name == "nt" else ""))
        )
        payload = root / "src" / f"{name}_distr" / "payload" / "app_lifecycle"
        (payload / "actions.py").write_text(
            '"""Consumer-owned setup and cleanup actions."""\n'
            "import os\n"
            "from pathlib import Path\n\n"
            "def prepare_project(prepared, project_directory):\n"
            '    Path(os.environ["LIFECYCLE_CUSTOM_STATE"]).write_text(\n'
            '        str(project_directory), encoding="utf-8"\n'
            "    )\n\n"
            "def cleanup_project(_context):\n"
            '    Path(os.environ["LIFECYCLE_CUSTOM_STATE"]).unlink()\n'
            '    executable = Path(os.environ["LIFECYCLE_CUSTOM_BIN"])\n'
            '    Path(os.environ["LIFECYCLE_CUSTOM_RESULT"]).write_text(\n'
            '        "present" if executable.exists() else "missing", encoding="utf-8"\n'
            "    )\n",
            encoding="utf-8",
        )
        install = payload / "install.py"
        install_source = install.read_text(encoding="utf-8")
        install_source = install_source.replace(
            "        prepared = selection.prepare(Path(staging))\n",
            "        prepared = selection.prepare(Path(staging))\n"
            "        if selection.source.kind != 'editable':\n"
            '            raise RuntimeError("Custom project setup requires an editable source.")\n'
            "        from .actions import prepare_project\n\n"
            "        prepare_project(prepared, Path(selection.source.requirement))\n",
            1,
        )
        install.write_text(install_source, encoding="utf-8")
        uninstall = payload / "uninstall.py"
        uninstall_source = uninstall.read_text(encoding="utf-8")
        uninstall_source = uninstall_source.replace(
            "    handoff = start_uninstall_handoff(\n"
            "        preparation.plan,\n"
            "        original_pid=original_pid or os.getpid(),\n"
            "    )\n",
            "    from .actions import cleanup_project\n\n"
            "    handoff = start_uninstall_handoff(\n"
            "        preparation.plan,\n"
            "        original_pid=original_pid or os.getpid(),\n"
            "        provider_cleanup=cleanup_project,\n"
            "    )\n",
            1,
        )
        uninstall.write_text(uninstall_source, encoding="utf-8")
    build = subprocess.run(
        [sys.executable, "-m", f"{name}_distr.make_artifacts"],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    check = subprocess.run(
        [sys.executable, "-m", f"{name}_distr.make_artifacts", "--check"],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    settings = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    app_id = settings["tool"]["apprc"]["distribution"]["app-id"]
    if os.name == "nt":
        state = Path(environment["LOCALAPPDATA"]) / app_id / "installation"
    elif sys.platform == "darwin":
        state = (
            Path(environment["HOME"])
            / "Library"
            / "Application Support"
            / app_id
            / "installation"
        )
    else:
        state = Path(environment["XDG_DATA_HOME"]) / app_id / "installation"
    return root, environment, state


@pytest.fixture
def consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Path, dict[str, str], Path]]:
    """Create a generated consumer with isolated native installation roots."""
    yield _create_consumer(tmp_path, monkeypatch, name="lifecycle_consumer")


def _run(
    command: list[str], *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True, check=False
    )


def _run_launcher_pty(
    executable: Path, *, cwd: Path, env: dict[str, str], marker: bytes
) -> tuple[int, bytes]:
    """Run the actual management launcher until its diagnostic is visible."""
    import pty

    environment = env | {"TERM": "xterm-256color", "COLUMNS": "120", "LINES": "40"}
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [str(executable), "launcher"],
        cwd=cwd,
        env=environment,
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)
    output = bytearray()
    try:
        deadline = time.monotonic() + 20
        while marker not in re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", bytes(output)):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    f"Launcher did not display {marker!r}: {bytes(output)!r}"
                )
            readable, _, _ = select.select([master], [], [], remaining)
            if readable:
                output.extend(os.read(master, 65536))
        os.write(master, b"q")
        return process.wait(timeout=20), bytes(output)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        os.close(master)


def _installer(root: Path, name: str) -> Path:
    """Return the generated main installer used for saved repair tests."""
    return (
        root / "src" / f"{name}_distr" / "artifacts" / "installer" / "main-installer.py"
    )


def _install_command(root: Path, *arguments: str) -> list[str]:
    """Invoke the actual AppRC-generated project-root installation wrapper."""
    entry = root / ("app-install.cmd" if os.name == "nt" else "app-install.sh")
    if os.name == "nt":
        return ["cmd.exe", "/d", "/c", str(entry), *arguments]
    return [str(entry), *arguments]


def _uninstall_command(state: Path) -> list[str]:
    if os.name == "nt":
        return ["cmd.exe", "/d", "/c", str(state / "uninstall.cmd"), "--yes"]
    return [str(state / "uninstall.sh"), "--yes"]


def test_generated_consumer_install_uses_installer_location_and_launches(
    consumer: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    root, environment, state = consumer
    name = "lifecycle_consumer"
    unrelated = tmp_path / "unrelated caller directory"
    unrelated.mkdir()
    result = _run(
        _install_command(root, "--layout", "native"),
        cwd=unrelated,
        env=environment,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / (
        name + (".exe" if os.name == "nt" else "")
    )
    paths = _run(
        [str(executable), "config", "paths", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert paths.returncode == 0, paths.stdout + paths.stderr
    authority = state / "installation.json"
    valid_authority = authority.read_bytes()
    authority.write_text("{invalid", encoding="utf-8")
    invalid_authority_paths = _run(
        [str(executable), "config", "paths", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert invalid_authority_paths.returncode != 0
    shown = _run(
        [str(executable), "installation", "show", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert shown.returncode == 0, shown.stdout + shown.stderr
    assert '"status": "invalid"' in shown.stdout
    diagnosed = _run(
        [str(executable), "installation", "doctor", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert diagnosed.returncode == 1
    assert '"status": "invalid"' in diagnosed.stdout
    preview = _run(
        [str(executable), "installation", "uninstall", "--dry-run", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert preview.returncode == 0, preview.stdout + preview.stderr
    if os.name != "nt":
        status, recovery_output = _run_launcher_pty(
            executable,
            cwd=unrelated,
            env=environment,
            marker=b'"installation_status": "invalid"',
        )
        assert status == 0
        assert b"Repair" in re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", recovery_output)
    authority.write_bytes(valid_authority)
    launcher = root / ("app-launch.cmd" if os.name == "nt" else "app-launch.sh")
    launch_command = (
        ["cmd.exe", "/d", "/c", str(launcher), "version"]
        if os.name == "nt"
        else [str(launcher), "version"]
    )
    launched = _run(launch_command, cwd=unrelated, env=environment)
    assert launched.returncode == 0, launched.stdout + launched.stderr
    assert launched.stdout.strip() == "0.1.0"
    command_source = root / "src" / name / "cli" / "app.py"
    command_text = command_source.read_text(encoding="utf-8")
    command_source.write_text(
        command_text.replace(
            "typer.echo(_package_version())",
            'typer.echo("editable source changed")',
            1,
        ),
        encoding="utf-8",
    )
    changed = _run([str(executable), "version"], cwd=unrelated, env=environment)
    assert changed.returncode == 0, changed.stdout + changed.stderr
    assert changed.stdout.strip() == "editable source changed"
    recorded_tool_dir = environment["UV_TOOL_DIR"]
    recorded_tool_bin = environment["UV_TOOL_BIN_DIR"]
    misleading_tools = tmp_path / "misleading tools"
    misleading_bins = tmp_path / "misleading bins"
    misleading_tools.mkdir()
    misleading_bins.mkdir()
    environment["UV_TOOL_DIR"] = str(misleading_tools)
    environment["UV_TOOL_BIN_DIR"] = str(misleading_bins)
    reinstalled = _run(
        _install_command(root, "--layout", "native"),
        cwd=unrelated,
        env=environment,
    )
    assert reinstalled.returncode == 0, reinstalled.stdout + reinstalled.stderr
    environment["UV_TOOL_DIR"] = recorded_tool_dir
    environment["UV_TOOL_BIN_DIR"] = recorded_tool_bin
    assert executable.is_file()
    launched = _run([str(executable), "--help"], cwd=unrelated, env=environment)
    assert launched.returncode == 0, launched.stdout + launched.stderr


def test_generated_consumer_root_wrappers_are_exactly_sdk_owned(
    consumer: tuple[Path, dict[str, str], Path],
) -> None:
    root, _, _ = consumer
    expected = {
        "app-install.sh",
        "app-install.cmd",
        "app-launch.sh",
        "app-launch.cmd",
        "app-uninstall.sh",
        "app-uninstall.cmd",
    }
    wrappers = {
        path.name
        for path in root.iterdir()
        if path.name.startswith(("app-install", "app-launch", "app-uninstall"))
    }
    assert wrappers == expected
    assert not any(
        (root / name).exists()
        for name in ("install.sh", "install.cmd", "uninstall.sh", "uninstall.cmd")
    )


def test_saved_default_uninstall_retains_recovery_support(
    consumer: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    root, environment, state = consumer
    name = "lifecycle_consumer"
    installed = _run(
        [sys.executable, str(_installer(root, name)), "--layout", "native"],
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    initial_record = json.loads(
        (state / "installation.json").read_text(encoding="utf-8")
    )
    saved_snapshot = initial_record["current"]
    assert saved_snapshot is not None
    uninstall = state / ("uninstall.cmd" if os.name == "nt" else "uninstall.sh")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    app_id = project["tool"]["apprc"]["distribution"]["app-id"]
    if os.name == "nt":
        appdata = Path(environment["LOCALAPPDATA"]) / app_id
    elif sys.platform == "darwin":
        appdata = Path(environment["HOME"]) / "Library" / "Application Support" / app_id
    else:
        appdata = Path(environment["XDG_DATA_HOME"]) / app_id / "appdata"
    appdata.mkdir(parents=True, exist_ok=True)
    retained = appdata / "retained-by-default.txt"
    retained.write_text("keep user data\n", encoding="utf-8")
    unknown = Path(environment["HOME"]) / "unknown-user-data.txt"
    unknown.write_text("leave unowned data untouched\n", encoding="utf-8")
    removed = _run(_uninstall_command(state), cwd=tmp_path, env=environment)
    assert removed.returncode == 0, removed.stdout + removed.stderr
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert record["status"] == "removed-retained"
    assert record["current"] is None
    assert record["last_successful"] is not None
    assert uninstall.is_file()
    assert retained.read_text(encoding="utf-8") == "keep user data\n"
    assert unknown.read_text(encoding="utf-8") == "leave unowned data untouched\n"
    tool_dir = Path(environment["UV_TOOL_DIR"])
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / (
        name + (".exe" if os.name == "nt" else "")
    )
    assert not (tool_dir / name).exists()
    assert not (tool_dir / name.replace("_", "-")).exists()
    assert not executable.exists()

    unrelated = tmp_path / "repair caller outside checkout"
    unrelated.mkdir()
    repaired = _run(
        [sys.executable, str(state / "repair-installer.py")],
        cwd=unrelated,
        env=environment,
    )
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert executable.is_file()
    repaired_record = json.loads(
        (state / "installation.json").read_text(encoding="utf-8")
    )
    assert repaired_record["status"] == "ready"
    assert repaired_record["current"] is not None
    assert repaired_record["current"]["source"] == saved_snapshot["source"]
    assert repaired_record["current"]["backend"] == saved_snapshot["backend"]
    runs = _run([str(executable), "--help"], cwd=unrelated, env=environment)
    assert runs.returncode == 0, runs.stdout + runs.stderr

    removed_again = _run(_uninstall_command(state), cwd=unrelated, env=environment)
    assert removed_again.returncode == 0, removed_again.stdout + removed_again.stderr
    retained_record = json.loads(
        (state / "installation.json").read_text(encoding="utf-8")
    )
    assert retained_record["status"] == "removed-retained"
    assert retained_record["current"] is None
    assert retained.exists()
    assert unknown.read_text(encoding="utf-8") == "leave unowned data untouched\n"
    assert uninstall.is_file()
    assert not executable.exists()


@pytest.mark.skipif(
    os.name == "nt", reason="The maintained TUI driver uses a POSIX PTY."
)
def test_launcher_saved_uninstall_waits_for_initiating_process_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the actual Textual launcher and its saved uninstall handoff in a PTY."""
    import pty

    root, environment, state = _create_consumer(
        tmp_path, monkeypatch, name="lifecycle_consumer", custom_actions=True
    )
    name = "lifecycle_consumer"
    installed = _run(
        [sys.executable, str(_installer(root, name)), "--layout", "native"],
        cwd=root,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / name
    environment.update(TERM="xterm-256color", COLUMNS="120", LINES="40")
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [str(executable), "launcher"],
        cwd=Path(environment["HOME"]),
        env=environment,
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)
    output = bytearray()

    def read_until(marker: bytes) -> None:
        deadline = time.monotonic() + 20
        while marker not in re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", bytes(output)):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    f"Launcher did not display {marker!r}: {bytes(output)!r}"
                )
            readable, _, _ = select.select([master], [], [], remaining)
            if not readable:
                continue
            try:
                output.extend(os.read(master, 65536))
            except OSError:
                break

    try:
        read_until(b"Run lifecycle_consumer")
        os.write(master, b"\x1b[Z\x1b[Z")
        os.write(master, b"\r")
        read_until(b"Remove application program")
        os.write(master, b"\r")
        assert process.wait(timeout=30) == 0, bytes(output).decode(errors="replace")
        deadline = time.monotonic() + 20
        authority = state / "installation.json"
        while time.monotonic() < deadline:
            if authority.is_file():
                record = json.loads(authority.read_text(encoding="utf-8"))
                if record["status"] == "removed-retained":
                    break
            time.sleep(0.05)
        record = json.loads(authority.read_text(encoding="utf-8"))
        assert record["status"] == "removed-retained"
        assert record["current"] is None
        assert not executable.exists()
        assert (state / "uninstall.sh").is_file()
        assert not Path(environment["LIFECYCLE_CUSTOM_STATE"]).exists()
        assert (
            Path(environment["LIFECYCLE_CUSTOM_RESULT"]).read_text(encoding="utf-8")
            == "present"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        os.close(master)


def test_custom_project_setup_and_cleanup_run_in_real_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = "custom_lifecycle_consumer"
    root, environment, state = _create_consumer(
        tmp_path, monkeypatch, name=name, custom_actions=True
    )
    marker = Path(environment["LIFECYCLE_CUSTOM_STATE"])
    installed = _run(
        [sys.executable, str(_installer(root, name)), "--layout", "native"],
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8") == str(root)
    executable = Path(environment["LIFECYCLE_CUSTOM_BIN"])
    removed = _run(
        [str(executable), "installation", "uninstall", "--yes"],
        cwd=tmp_path,
        env=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not marker.exists()
    assert (
        Path(environment["LIFECYCLE_CUSTOM_RESULT"]).read_text(encoding="utf-8")
        == "present"
    )
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert record["status"] == "removed-retained"
    assert record["current"] is None
    assert record["last_successful"] is not None
    assert not Path(environment["LIFECYCLE_CUSTOM_BIN"]).exists()
    assert (state / "installation.json").is_file()


def test_saved_support_link_failure_preserves_installation_for_recovery(
    consumer: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    """Reject linked saved support without deleting the app, then recover."""
    root, environment, state = consumer
    installed = _run(
        [
            sys.executable,
            str(_installer(root, "lifecycle_consumer")),
            "--layout",
            "native",
        ],
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    inspection = state / "inspection.py"
    saved_inspection = inspection.read_bytes()
    outside = tmp_path / "linked inspection.py"
    outside.write_bytes(saved_inspection)
    inspection.unlink()
    inspection.symlink_to(outside)
    failed = _run(_uninstall_command(state), cwd=tmp_path, env=environment)
    assert failed.returncode != 0
    command = Path(environment["UV_TOOL_BIN_DIR"]) / "lifecycle_consumer"
    assert command.is_file()
    inspection.unlink()
    inspection.write_bytes(saved_inspection)
    recovered = _run(_uninstall_command(state), cwd=tmp_path, env=environment)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert not command.exists()


def test_generated_support_directory_link_is_rejected(
    consumer: tuple[Path, dict[str, str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a linked lifecycle support directory before reading its contents."""
    import importlib.util

    root, _, _ = consumer
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    app_id = project["tool"]["apprc"]["distribution"]["app-id"]
    payload = root / "src" / "lifecycle_consumer_distr" / "payload"
    lifecycle = payload / "app_lifecycle"
    support = lifecycle / "_support"
    outside = tmp_path / "external support"
    shutil.copytree(support, outside)
    shutil.rmtree(support)
    support.symlink_to(outside, target_is_directory=True)
    module_spec = importlib.util.spec_from_file_location(
        "generated_lifecycle_install",
        lifecycle / "install.py",
    )
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "path", [str(payload), *sys.path[1:]])
    monkeypatch.setattr(
        sys, "argv", [str(tmp_path / "unmanaged" / "main-installer.py")]
    )
    with pytest.raises(RuntimeError, match="support directory is missing or linked"):
        module._support_files(app_id)


@pytest.mark.parametrize(
    ("legacy_package", "interruption"),
    [
        ("editable", None),
        ("wheel", None),
        ("editable", "retire"),
        ("editable", "promote"),
        ("editable", "receipt"),
    ],
)
def test_legacy_receipt_conflicts_then_cutover_preserves_runnable_recovery(
    consumer: tuple[Path, dict[str, str], Path],
    tmp_path: Path,
    interruption: str | None,
    legacy_package: str,
) -> None:
    """Keep legacy authority intact when conflicts prevent a safe cutover."""
    root, environment, state = consumer
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    metadata = project["project"]
    distribution = re.sub(r"[-_.]+", "-", metadata["name"]).lower()
    command = next(iter(metadata["scripts"]))
    installed = _run(
        _install_command(root, "--layout", "native"),
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    prior = json.loads((state / "installation.json").read_text(encoding="utf-8"))[
        "current"
    ]
    assert prior is not None
    source = prior["source"]
    record_digest = prior["distribution_record_digest"]
    wheel_to_restore: tuple[Path, bytes] | None = None
    if legacy_package == "wheel":
        from apprc.definition.installation import InstallationSource
        import dataclasses
        from apprc.distribution import read_project_metadata
        from apprc.distribution.runtime import installed_probe
        from apprc.distribution.runtime.acquisition import prepare_source
        from apprc.distribution.runtime.probe import probe_installed_tool
        from apprc.user_files.installation.discovery import inspect_installation
        from apprc.distribution.runtime.backend import install_uv_tool, select_uv_target
        from buildben_distr.make_artifacts import APPRC_COMMIT

        built = _run(["uv", "build", "--wheel"], cwd=root, env=environment)
        assert built.returncode == 0, built.stdout + built.stderr
        wheels = tuple((root / "dist").glob("*.whl"))
        assert len(wheels) == 1
        overrides = (
            f"apprc-core @ git+https://github.com/HisQu/apprc.git@{APPRC_COMMIT}",
            f"apprc @ git+https://github.com/HisQu/apprc.git@{APPRC_COMMIT}"
            "#subdirectory=src/apprc_dev/packaging/terminal",
        )
        wheel_digest = hashlib.sha256(wheels[0].read_bytes()).hexdigest()
        wheel_source = InstallationSource(
            "wheel",
            str(wheels[0]),
            version=metadata["version"],
            digest=wheel_digest,
            runtime_overrides=overrides,
        )
        target = select_uv_target(
            Path(environment["APPRC_UV_PATH"]),
            environment=environment,
            invocation_cwd=tmp_path,
        )
        prepared = prepare_source(wheel_source, tmp_path / "legacy-acquisition")
        install_uv_tool(
            target,
            dataclasses.replace(wheel_source, requirement=prepared.requirement),
            environment=environment,
            python_requirement=">=3.12",
        )
        identity = read_project_metadata(root).identity
        current_record = inspect_installation(state, app_id=identity.app_id).record
        assert current_record is not None
        observed = probe_installed_tool(
            target,
            identity,
            wheel_source,
            current_record.placement,
            probe_path=Path(installed_probe.__file__).absolute(),
            environment=environment,
            acquisition_requirement=prepared.requirement,
            acquisition_digest=prepared.digest,
        )
        source = json.loads(json.dumps(dataclasses.asdict(observed.source)))
        record_digest = observed.distribution_record_digest
        wheel_to_restore = (wheels[0], wheels[0].read_bytes())
        wheels[0].unlink()
        shutil.rmtree(tmp_path / "legacy-acquisition")
        project_file = root / "pyproject.toml"
        text = project_file.read_text(encoding="utf-8")
        text = text.replace(
            f'version     = "{metadata["version"]}"', 'version     = "0.2.0"'
        )
        project_file.write_text(text, encoding="utf-8")
        generated = _run(
            [sys.executable, "-m", "lifecycle_consumer_distr.make_artifacts"],
            cwd=root,
            env=environment,
        )
        assert generated.returncode == 0, generated.stdout + generated.stderr
    source_file = tmp_path / "legacy-source-evidence.json"
    source_file.write_text(
        json.dumps({"source": source, "distribution_record_digest": record_digest}),
        encoding="utf-8",
    )

    legacy_base = (
        Path(environment["LOCALAPPDATA"])
        if os.name == "nt"
        else Path(environment["XDG_STATE_HOME"])
    )
    legacy_root = legacy_base / distribution / "installation"
    if state.exists():
        shutil.rmtree(state)
    if legacy_root.exists():
        shutil.rmtree(legacy_root)
    legacy_root.mkdir(parents=True)
    receipt = {
        "schema_version": 1,
        "distribution": distribution,
        "command": command,
        "version": metadata["version"],
        "source_ref": f"v{metadata['version']}",
        "python": str(Path(sys.executable).resolve()),
        "uv": environment["APPRC_UV_PATH"],
        "tool_dir": environment["UV_TOOL_DIR"],
        "tool_bin_dir": environment["UV_TOOL_BIN_DIR"],
        "appdata_supported": False,
        "uv_bootstrapped": False,
        "uv_binaries": [],
        "package_removed": False,
    }
    (legacy_root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    for name in (
        "lifecycle.py",
        "uninstall.sh",
        "uninstall.cmd",
        "uninstall.ps1",
        "prepare-powershell-windows.cmd",
    ):
        (legacy_root / name).write_text("legacy support\n", encoding="utf-8")
    unknown = legacy_root / "unknown-user-file.txt"
    unknown.write_text("preserve unknown content\n", encoding="utf-8")

    migration = (
        "--migrate-legacy",
        "--legacy-quiescent",
        "--legacy-source",
        str(source_file),
        "--layout",
        "native",
    )
    unrequested = _run(
        _install_command(root, "--layout", "native"),
        cwd=tmp_path,
        env=environment,
    )
    assert unrequested.returncode != 0
    assert (legacy_root / "receipt.json").is_file()
    missing_layout = _run(
        _install_command(root, "--migrate-legacy", "--legacy-quiescent"),
        cwd=tmp_path,
        env=environment,
    )
    assert missing_layout.returncode != 0
    assert (legacy_root / "receipt.json").is_file()
    blocked = _run(
        _install_command(root, *migration),
        cwd=tmp_path,
        env=environment,
    )
    assert blocked.returncode != 0
    assert (legacy_root / "receipt.json").is_file()
    assert unknown.read_text(encoding="utf-8") == "preserve unknown content\n"
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / (
        command + (".exe" if os.name == "nt" else "")
    )
    assert executable.is_file()

    unknown.unlink()
    if interruption is not None:
        installer = _installer(root, "lifecycle_consumer")
        driver = Path(__file__).parent / "support_lifecycle_fault.py"
        interrupted = _run(
            [
                sys.executable,
                str(driver),
                "--boundary",
                interruption,
                str(installer),
                *migration,
            ],
            cwd=tmp_path,
            env=environment,
        )
        assert interrupted.returncode != 0
        pending = json.loads((state / "installation.json").read_text(encoding="utf-8"))
        assert pending["migration"] is not None
        assert not pending["migration"]["cleanup_complete"]
        assert executable.is_file()
    migrated = _run(_install_command(root, *migration), cwd=tmp_path, env=environment)
    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    assert not (legacy_root / "receipt.json").exists()
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert record["status"] == "ready"
    assert record["migration"]["cleanup_complete"]
    assert record["current"]["version"] == metadata["version"]
    assert record["current"]["source"] == source
    assert executable.is_file()
    for filename in ("launch-command.json", "uninstall.py", "repair-installer.py"):
        assert (state / filename).is_file()
    launched = _run([str(executable), "--help"], cwd=tmp_path, env=environment)
    assert launched.returncode == 0, launched.stdout + launched.stderr
    launch_command = (
        ["cmd.exe", "/d", "/c", str(state / "launch.cmd"), "--help"]
        if os.name == "nt"
        else [str(state / "launch.sh"), "--help"]
    )
    saved_launch = _run(launch_command, cwd=tmp_path, env=environment)
    assert saved_launch.returncode == 0, saved_launch.stdout + saved_launch.stderr
    inspected = _run(
        [
            sys.executable,
            str(state / "inspection.py"),
            "--directory",
            str(state),
            "--app-id",
            project["tool"]["apprc"]["distribution"]["app-id"],
        ],
        cwd=tmp_path,
        env=environment,
    )
    assert inspected.returncode == 0, inspected.stdout + inspected.stderr
    if wheel_to_restore is not None:
        wheel_path, wheel_content = wheel_to_restore
        wheel_path.write_bytes(wheel_content)
    repaired = _run(
        [sys.executable, str(state / "repair-installer.py")],
        cwd=tmp_path,
        env=environment,
    )
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    removed = _run(_uninstall_command(state), cwd=tmp_path, env=environment)
    assert removed.returncode == 0, removed.stdout + removed.stderr
    final = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert final["status"] == "removed-retained"
    assert final["current"] is None
    assert not executable.exists()
