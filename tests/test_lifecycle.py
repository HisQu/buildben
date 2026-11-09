"""Real generated-consumer lifecycle smoke tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import select
import subprocess
import struct
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
    import fcntl
    import pty
    import termios

    environment = env | {"TERM": "xterm-256color", "COLUMNS": "120", "LINES": "40"}
    master, slave = pty.openpty()

    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
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
        while True:
            ready = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", bytes(output))
            if marker in ready and b"Repair" in ready:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    f"Launcher did not render {marker!r} and its Repair action: {bytes(output)!r}"
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


def _uninstall_command(state: Path, *arguments: str) -> list[str]:
    forwarded = arguments or ("--yes",)
    if os.name == "nt":
        return ["cmd.exe", "/d", "/c", str(state / "uninstall.cmd"), *forwarded]
    return [str(state / "uninstall.sh"), *forwarded]


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
        rendered = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", recovery_output)
        assert b'"installation_status": "invalid"' in rendered
        assert b"Repair" in rendered
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


def test_external_repair_rejects_another_app_identity(
    consumer: tuple[Path, dict[str, str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An external installer cannot repair a different app's authority."""
    root, environment, state = consumer
    installed = _run(
        _install_command(root, "--layout", "native"),
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    other_workspace = tmp_path / "other consumer workspace"
    other_workspace.mkdir()
    other_root, other_environment, other_state = _create_consumer(
        other_workspace, monkeypatch, name="other_lifecycle_consumer"
    )
    other_install = _run(
        _install_command(other_root, "--layout", "native"),
        cwd=tmp_path,
        env=other_environment,
    )
    assert other_install.returncode == 0, other_install.stdout + other_install.stderr
    prior_authority = (other_state / "installation.json").read_bytes()
    refused = _run(
        [
            sys.executable,
            str(_installer(root, "lifecycle_consumer")),
            "--repair",
            "--directory",
            str(other_state),
        ],
        cwd=tmp_path,
        env=environment,
    )
    assert refused.returncode != 0
    assert (other_state / "installation.json").read_bytes() == prior_authority


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
    wrong_directory = tmp_path / "not the saved installation"
    wrong_directory.mkdir()
    refused = _run(
        [
            sys.executable,
            str(state / "repair-installer.py"),
            "--repair",
            "--directory",
            str(wrong_directory),
        ],
        cwd=unrelated,
        env=environment,
    )
    assert refused.returncode != 0
    unchanged = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert unchanged["status"] == "removed-retained"
    misleading_tools = tmp_path / "misleading repair tools"
    misleading_bins = tmp_path / "misleading repair bins"
    misleading_tools.mkdir()
    misleading_bins.mkdir()
    repair_environment = environment | {
        "UV_TOOL_DIR": str(misleading_tools),
        "UV_TOOL_BIN_DIR": str(misleading_bins),
    }
    repaired = _run(
        [
            sys.executable,
            str(state / "repair-installer.py"),
            "--repair",
            "--directory",
            str(state),
        ],
        cwd=unrelated,
        env=repair_environment,
    )
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert executable.is_file()
    assert not tuple(misleading_tools.iterdir())
    assert not tuple(misleading_bins.iterdir())
    repaired_record = json.loads(
        (state / "installation.json").read_text(encoding="utf-8")
    )
    assert repaired_record["status"] == "ready"
    assert repaired_record["current"] is not None
    assert repaired_record["current"]["source"] == saved_snapshot["source"]
    assert repaired_record["current"]["backend"] == saved_snapshot["backend"]
    runs = _run([str(executable), "--help"], cwd=unrelated, env=environment)
    saved_repair = _run(
        [sys.executable, str(state / "repair-installer.py")],
        cwd=unrelated,
        env=environment,
    )
    assert saved_repair.returncode == 0, saved_repair.stdout + saved_repair.stderr
    assert executable.is_file()
    assert runs.returncode == 0, runs.stdout + runs.stderr

    external_repair = _run(
        [
            sys.executable,
            str(_installer(root, "lifecycle_consumer")),
            "--repair",
            "--directory",
            str(state),
        ],
        cwd=unrelated,
        env=environment,
    )
    assert external_repair.returncode == 0, (
        external_repair.stdout + external_repair.stderr
    )
    wrong_external_address = _run(
        [
            sys.executable,
            str(_installer(root, "lifecycle_consumer")),
            "--repair",
            "--directory",
            str(wrong_directory),
        ],
        cwd=unrelated,
        env=environment,
    )
    assert wrong_external_address.returncode != 0
    assert (
        json.loads((state / "installation.json").read_text(encoding="utf-8"))["status"]
        == "ready"
    )

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


def test_saved_complete_uninstall_removes_owned_lifecycle_authority(
    consumer: tuple[Path, dict[str, str], Path],
    tmp_path: Path,
) -> None:
    """Complete removal deletes the recorded program and owned support last."""
    root, environment, state = consumer
    name = "lifecycle_consumer"
    installed = _run(
        [sys.executable, str(_installer(root, name)), "--layout", "native"],
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / name
    assert executable.is_file()
    removed = _run(
        _uninstall_command(state, "--complete", "--yes"),
        cwd=tmp_path,
        env=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not executable.exists()
    assert not (state / "installation.json").exists()
    assert not (state / "repair-installer.py").exists()


@pytest.mark.skipif(
    os.name == "nt", reason="The maintained TUI driver uses a POSIX PTY."
)
def test_launcher_saved_uninstall_waits_for_initiating_process_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the actual Textual launcher and its saved uninstall handoff in a PTY."""
    import pty
    import termios
    import fcntl

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
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
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
        read_until(b"Remove program")
        os.write(master, b"\x1b[Z\x1b[Z\r")
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
        ("replacement", None),
        ("replacement", "before-backend"),
        ("replacement", "after-backend"),
        ("replacement", "authority"),
        ("replacement", "retire"),
        ("replacement", "ready-order"),
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
    legacy_python = Path(sys.executable).resolve()
    if legacy_package == "wheel":
        from apprc.definition.installation import InstallationSource
        import dataclasses
        from apprc.distribution import read_project_metadata
        from apprc.distribution.runtime import installed_probe
        from apprc.distribution.runtime.acquisition import prepare_source
        from apprc.distribution.runtime.probe import probe_installed_tool
        from apprc.user_files.installation.discovery import inspect_installation
        from apprc.distribution.runtime.backend import (
            external_base_python,
            install_uv_tool,
            select_uv_target,
        )
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
        legacy_python = external_base_python(target.tool_dir / distribution)
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
    observed_legacy = None
    if legacy_package == "replacement":
        import dataclasses
        from urllib.parse import urlsplit
        from urllib.request import url2pathname

        from apprc.definition.installation import InstallationSource
        from apprc.distribution import read_project_metadata
        from apprc.distribution.runtime import installed_probe
        from apprc.distribution.runtime.backend import (
            external_base_python,
            select_uv_target,
            tool_interpreter,
        )
        from buildben_distr.make_artifacts import APPRC_COMMIT

        identity = read_project_metadata(root).identity
        overrides = (
            f"apprc-core @ git+https://github.com/HisQu/apprc.git@{APPRC_COMMIT}",
            f"apprc @ git+https://github.com/HisQu/apprc.git@{APPRC_COMMIT}"
            "#subdirectory=src/apprc_dev/packaging/terminal",
        )
        legacy_source_root = tmp_path / "legacy-source-archive"
        shutil.copytree(
            root,
            legacy_source_root,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "__pycache__", "*.pyc", "dist"
            ),
        )
        target = select_uv_target(
            Path(environment["APPRC_UV_PATH"]),
            environment=environment,
            invocation_cwd=tmp_path,
        )
        legacy_python = Path(sys.executable).resolve()
        historical_install = _run(
            [
                str(target.executable),
                "tool",
                "install",
                "--force",
                "--python",
                str(legacy_python),
                "--from",
                str(legacy_source_root),
                "--with",
                overrides[0],
                "--with",
                overrides[1],
                distribution,
            ],
            cwd=tmp_path,
            env=environment,
        )
        assert historical_install.returncode == 0, (
            historical_install.stdout + historical_install.stderr
        )
        legacy_python = external_base_python(target.tool_dir / distribution)
        observed_legacy = _run(
            [
                str(tool_interpreter(target, distribution)),
                "-I",
                str(Path(installed_probe.__file__).absolute()),
                "--distribution",
                distribution,
                "--app-id",
                identity.app_id,
                "--import-package",
                identity.import_package,
                *(
                    item
                    for command_name in identity.commands
                    for item in ("--command", command_name)
                ),
            ],
            cwd=tmp_path,
            env=environment,
        )
        assert observed_legacy.returncode == 0, (
            observed_legacy.stdout + observed_legacy.stderr
        )
        legacy_observation = json.loads(observed_legacy.stdout)
        assert legacy_observation["version"] == metadata["version"]
        assert isinstance(legacy_observation["distribution_record_digest"], str)
        assert len(legacy_observation["distribution_record_digest"]) == 64
        direct_url = legacy_observation["direct_url"]
        assert isinstance(direct_url, dict)
        source_url = direct_url["url"]
        assert isinstance(source_url, str)
        assert Path(url2pathname(urlsplit(source_url).path)).resolve() == (
            legacy_source_root.resolve()
        )
        assert isinstance(direct_url.get("dir_info"), dict)
        assert direct_url["dir_info"].get("editable", False) is False
        record_digest = legacy_observation["distribution_record_digest"]
        shutil.rmtree(legacy_source_root)
        assert not legacy_source_root.exists()
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
        built = _run(["uv", "build", "--wheel"], cwd=root, env=environment)
        assert built.returncode == 0, built.stdout + built.stderr
        replacement_wheels = tuple((root / "dist").glob("*.whl"))
        assert len(replacement_wheels) == 1
        replacement_digest = hashlib.sha256(
            replacement_wheels[0].read_bytes()
        ).hexdigest()
        replacement_source = InstallationSource(
            "wheel",
            str(replacement_wheels[0]),
            version="0.2.0",
            digest=replacement_digest,
            runtime_overrides=overrides,
        )
        source = json.loads(json.dumps(dataclasses.asdict(replacement_source)))
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
    retained_payload: Path | None = None
    if legacy_package == "replacement":
        app_id = project["tool"]["apprc"]["distribution"]["app-id"]
        assert isinstance(app_id, str)
        if os.name == "nt":
            appdata = Path(environment["LOCALAPPDATA"]) / app_id / "appdata" / "appdata"
        elif sys.platform == "darwin":
            appdata = (
                Path(environment["HOME"])
                / "Library"
                / "Application Support"
                / app_id
                / "appdata"
                / "appdata"
            )
        else:
            appdata = (
                Path(environment["XDG_DATA_HOME"]) / app_id / "appdata" / "appdata"
            )
        appdata.mkdir(parents=True, exist_ok=True)
        retained_payload = appdata / "replacement-payload.txt"
        retained_payload.write_text("preserve user payload\n", encoding="utf-8")
        missing_quiescence = _run(
            _install_command(
                root,
                "--migrate-legacy",
                "--reinstall-legacy",
                "--layout",
                "native",
                "--legacy-source",
                str(source_file),
            ),
            cwd=tmp_path,
            env=environment,
        )
        assert missing_quiescence.returncode != 0
        assert not (state / "installation.json").exists()
    receipt = {
        "schema_version": 1,
        "distribution": distribution,
        "command": command,
        "version": metadata["version"],
        "source_ref": f"v{metadata['version']}",
        "python": str(legacy_python),
        "uv": environment["APPRC_UV_PATH"],
        "tool_dir": environment["UV_TOOL_DIR"],
        "tool_bin_dir": environment["UV_TOOL_BIN_DIR"],
        "appdata_supported": False,
        "uv_bootstrapped": False,
        "uv_binaries": [],
        "package_removed": False,
    }

    invalid_reinstall = _run(
        _install_command(root, "--reinstall-legacy"),
        cwd=tmp_path,
        env=environment,
    )
    assert invalid_reinstall.returncode != 0
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
    explicit_migration = (
        (*migration, "--reinstall-legacy")
        if legacy_package == "replacement"
        else migration
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

    if legacy_package == "replacement":
        replacement_blocked = _run(
            _install_command(root, *explicit_migration),
            cwd=tmp_path,
            env=environment,
        )
        assert replacement_blocked.returncode != 0
        assert (legacy_root / "receipt.json").is_file()
        assert executable.is_file()
        assert not (state / "installation.json").exists()
    unknown.unlink()
    if legacy_package == "replacement":
        strict_adoption = _run(
            _install_command(root, *migration), cwd=tmp_path, env=environment
        )
        assert strict_adoption.returncode != 0
        assert (legacy_root / "receipt.json").is_file()
        assert executable.is_file()
        assert not (state / "installation.json").exists()
        wrong_record = json.loads(source_file.read_text(encoding="utf-8"))
        wrong_record["distribution_record_digest"] = "0" * 64
        source_file.write_text(json.dumps(wrong_record), encoding="utf-8")
        mismatched = _run(
            _install_command(root, *explicit_migration),
            cwd=tmp_path,
            env=environment,
        )
        assert mismatched.returncode != 0
        assert not (state / "installation.json").exists()
        assert (legacy_root / "receipt.json").is_file()
        assert executable.is_file()
        source_file.write_text(
            json.dumps(
                {
                    "source": source,
                    "distribution_record_digest": record_digest,
                }
            ),
            encoding="utf-8",
        )
    pending = None
    if interruption is not None:
        installer = _installer(root, "lifecycle_consumer")
        driver = Path(__file__).parent / "support_lifecycle_fault.py"
        interrupted_arguments = [
            sys.executable,
            str(driver),
            "--boundary",
            interruption,
        ]
        if interruption == "ready-order":
            interrupted_arguments.extend(("--legacy-root", str(legacy_root)))
        interrupted_arguments.extend((str(installer), *explicit_migration))
        interrupted = _run(
            interrupted_arguments,
            cwd=tmp_path,
            env=environment,
        )
        if interruption == "ready-order":
            assert interrupted.returncode == 0, interrupted.stdout + interrupted.stderr
        else:
            assert interrupted.returncode != 0
            pending = json.loads(
                (state / "installation.json").read_text(encoding="utf-8")
            )
            if legacy_package == "replacement" and interruption != "retire":
                assert pending["migration"] is None
                assert pending["operation"]["kind"] == "replace"
            elif legacy_package == "replacement":
                assert pending["migration"] is not None
                assert pending["operation"]["kind"] == "migrate"
            else:
                assert pending["migration"] is not None
                assert not pending["migration"]["cleanup_complete"]
            if legacy_package == "replacement":
                pending_before_recovery = (state / "installation.json").read_bytes()
                missing_consent = _run(
                    [
                        sys.executable,
                        str(_installer(root, "lifecycle_consumer")),
                        "--repair",
                        "--directory",
                        str(state),
                    ],
                    cwd=tmp_path,
                    env=environment,
                )
                assert missing_consent.returncode != 0
                recovery_message = missing_consent.stdout + missing_consent.stderr
                assert "--legacy-quiescent" in recovery_message
                assert "--repair" in recovery_message
                assert str(_installer(root, "lifecycle_consumer")) in recovery_message
                assert str(state) in recovery_message
                assert sys.executable in recovery_message
                assert (
                    state / "installation.json"
                ).read_bytes() == pending_before_recovery
    if legacy_package == "replacement" and interruption is not None:
        if interruption == "ready-order":
            migrated = _run(
                [
                    sys.executable,
                    str(state / "repair-installer.py"),
                    "--repair",
                    "--directory",
                    str(state),
                ],
                cwd=tmp_path,
                env=environment,
            )
        elif interruption in {"before-backend", "after-backend"}:
            saved_repair = state / "repair-installer.py"
            assert saved_repair.is_file()
            assert pending is not None
            intended = pending["operation"]["intended"]
            assert intended["source"] == source
            assert intended["backend"] == prior["backend"]
            assert intended["placement"] == prior["placement"]
            pending_operation_id = pending["operation"]["operation_id"]
            replacement_archive = Path(source["requirement"])
            replacement_content = replacement_archive.read_bytes()
            replacement_archive.unlink()
            source_file.unlink()
            unavailable_checkout = root.with_name(root.name + "-unavailable")
            root.rename(unavailable_checkout)
            assert not root.exists()
            assert not replacement_archive.exists()
            assert not source_file.exists()
            migrated = _run(
                [
                    sys.executable,
                    str(saved_repair),
                    "--repair",
                    "--directory",
                    str(state),
                    "--legacy-quiescent",
                ],
                cwd=tmp_path,
                env=environment,
            )
            assert migrated.returncode == 0, migrated.stdout + migrated.stderr
            recovered = json.loads(
                (state / "installation.json").read_text(encoding="utf-8")
            )
            assert recovered["status"] == "ready"
            assert recovered["operation"] is None
            assert recovered["migration"]["operation_id"] == pending_operation_id
            assert recovered["migration"]["cleanup_complete"]
            assert recovered["current"]["source"] == intended["source"]
            assert recovered["current"]["backend"] == intended["backend"]
            assert recovered["current"]["placement"] == intended["placement"]
            assert recovered["current"]["version"] == "0.2.0"
            assert not (legacy_root / "receipt.json").exists()
            assert not (legacy_root / "lifecycle.py").exists()
            assert retained_payload is not None
            assert retained_payload.read_text(encoding="utf-8") == (
                "preserve user payload\n"
            )
            assert observed_legacy is not None
            assert isinstance(observed_legacy.args, list)
            replacement_observed = _run(
                observed_legacy.args, cwd=tmp_path, env=environment
            )
            assert replacement_observed.returncode == 0, (
                replacement_observed.stdout + replacement_observed.stderr
            )
            replacement_metadata = json.loads(replacement_observed.stdout)
            assert replacement_metadata["version"] == "0.2.0"
            assert (
                replacement_metadata["distribution_record_digest"]
                == (recovered["current"]["distribution_record_digest"])
            )
            replacement_command = _run(
                [str(executable), "--help"], cwd=tmp_path, env=environment
            )
            assert replacement_command.returncode == 0, (
                replacement_command.stdout + replacement_command.stderr
            )
            assert not root.exists()
            assert not replacement_archive.exists()
            unavailable_checkout.rename(root)
            replacement_archive.write_bytes(replacement_content)
        else:
            source_file.unlink()
            if interruption == "retire":
                recovery_command = [
                    sys.executable,
                    str(_installer(root, "lifecycle_consumer")),
                    *explicit_migration,
                ]
            else:
                recovery_command = [
                    sys.executable,
                    str(_installer(root, "lifecycle_consumer")),
                    "--repair",
                    "--directory",
                    str(state),
                    "--legacy-quiescent",
                ]
            migrated = _run(
                recovery_command,
                cwd=tmp_path,
                env=environment,
            )
    else:
        migrated = _run(
            _install_command(root, *explicit_migration),
            cwd=tmp_path,
            env=environment,
        )
    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    assert not (legacy_root / "receipt.json").exists()
    assert not (legacy_root / "lifecycle.py").exists()
    if retained_payload is not None:
        assert retained_payload.read_text(encoding="utf-8") == "preserve user payload\n"
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    assert record["status"] == "ready"
    assert record["migration"]["cleanup_complete"]
    assert record["current"]["version"] == (
        "0.2.0" if legacy_package == "replacement" else metadata["version"]
    )
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
