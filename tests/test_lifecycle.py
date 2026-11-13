"""Real generated-consumer lifecycle smoke tests."""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import shutil
import struct
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
            frontend=None,
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
    environment["UV"] = str(Path(uv).resolve())
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
            "        prepared = selection.prepare(Path(staging).resolve())\n",
            "        prepared = selection.prepare(Path(staging).resolve())\n"
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
    executable: Path,
    *,
    cwd: Path,
    env: dict[str, str],
    marker: bytes,
    authority: Path,
) -> int:
    """Run the real management surface without replacing invalid authority."""
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
    authority_bytes = authority.read_bytes()
    try:
        deadline = time.monotonic() + 20
        while marker not in re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", bytes(output)):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    f"Launcher did not reach its management screen: {bytes(output)!r}"
                )
            readable, _, _ = select.select([master], [], [], remaining)
            if readable:
                output.extend(os.read(master, 65536))
        os.write(master, b"q")
        deadline = time.monotonic() + 20
        while process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError("Launcher did not exit after Quit.")
            readable, _, _ = select.select([master], [], [], min(remaining, 0.25))
            if readable:
                try:
                    output.extend(os.read(master, 65536))
                except OSError:
                    break
        status = process.wait(timeout=5)
        assert authority.read_bytes() == authority_bytes
        return status
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
    """Invoke the generated Python developer entry from any working directory."""
    entry = root / "app-install.py"
    return [sys.executable, str(entry), *arguments]


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
    assert json.loads(shown.stdout)["status"] == "invalid"
    diagnosed = _run(
        [str(executable), "installation", "doctor", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert diagnosed.returncode == 1
    assert json.loads(diagnosed.stdout)["status"] == "invalid"
    preview = _run(
        [str(executable), "installation", "uninstall", "--dry-run", "--json"],
        cwd=unrelated,
        env=environment,
    )
    assert preview.returncode == 0, preview.stdout + preview.stderr
    if os.name != "nt":
        status = _run_launcher_pty(
            executable,
            cwd=unrelated,
            env=environment,
            marker=b"AppRC launcher",
            authority=authority,
        )
        assert status == 0
    authority.write_bytes(valid_authority)
    launcher = root / "app-launch.py"
    launch_command = [sys.executable, str(launcher), "version"]
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove owned authority and program while explicitly retaining custom config."""
    root, environment, state = _create_consumer(
        tmp_path,
        monkeypatch,
        name="lifecycle_consumer",
        custom_actions=True,
    )
    name = "lifecycle_consumer"
    installed = _run(
        [sys.executable, str(_installer(root, name)), "--layout", "native"],
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    executable = Path(environment["UV_TOOL_BIN_DIR"]) / name
    assert executable.is_file()
    record = json.loads((state / "installation.json").read_text(encoding="utf-8"))
    config_root = Path(record["placement"]["config_dir"])
    custom_config = config_root / "custom-settings.toml"
    custom_config.write_text("user setting = true\n", encoding="utf-8")
    removed = _run(
        _uninstall_command(
            state,
            "--complete",
            "--category",
            "config",
            "--category",
            "appdata",
            "--forget-retained",
            "--yes",
        ),
        cwd=tmp_path,
        env=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not executable.exists()
    assert not (state / "installation.json").exists()
    assert not (state / "repair-installer.py").exists()
    assert custom_config.read_text(encoding="utf-8") == "user setting = true\n"
    assert not Path(environment["LIFECYCLE_CUSTOM_STATE"]).exists()
    assert (
        Path(environment["LIFECYCLE_CUSTOM_RESULT"]).read_text(encoding="utf-8")
        == "present"
    )


@pytest.mark.skipif(
    os.name == "nt", reason="The maintained TUI driver uses a POSIX PTY."
)
def test_launcher_saved_uninstall_waits_for_initiating_process_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the actual Textual launcher and its saved uninstall handoff in a PTY."""
    import fcntl
    import pty
    import termios

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
    environment.update(TERM="xterm-256color", COLUMNS="120", LINES="60")
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 60, 120, 0, 0))
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
            except OSError as error:
                raise AssertionError(
                    f"Launcher exited before displaying {marker!r}: {bytes(output)!r}"
                ) from error

    def click_button(label: bytes) -> None:
        """Click the current rendered label rather than guessing focus order."""
        read_until(label)
        rendered = bytes(output)
        label_at = rendered.rfind(label)
        positions = tuple(re.finditer(rb"\x1b\[(\d+);(\d+)H", rendered[:label_at]))
        assert label_at >= 0 and positions, rendered.decode(errors="replace")
        cursor = positions[-1]
        prefix = re.sub(
            rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", rendered[cursor.end() : label_at]
        ).decode("utf-8")
        row = int(cursor[1])
        column = int(cursor[2]) + len(prefix) + 1
        os.write(
            master,
            f"\x1b[<0;{column};{row}M\x1b[<0;{column};{row}m".encode(),
        )

    try:
        click_button(b"Uninstall")
        click_button(b"Remove program")
        authority = state / "installation.json"
        deadline = time.monotonic() + 30
        while process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(
                    "Launcher did not exit after saved uninstall confirmation: "
                    + bytes(output).decode(errors="replace")
                )
            readable, _, _ = select.select([master], [], [], min(remaining, 0.1))
            if readable:
                try:
                    output.extend(os.read(master, 65536))
                except OSError:
                    break
        assert process.wait(timeout=30) == 0, bytes(output).decode(errors="replace")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if authority.is_file():
                record = json.loads(authority.read_text(encoding="utf-8"))
                if record["status"] == "removed-retained":
                    break
            time.sleep(0.05)
        record = json.loads(authority.read_text(encoding="utf-8"))
        assert record["status"] == "removed-retained", bytes(output).decode(
            errors="replace"
        )
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


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="Linux resource migration paths.",
)
def test_saved_installer_resumes_interrupted_current_resource_migration(
    consumer: tuple[Path, dict[str, str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume schema-2 resource moves through the maintained installer."""
    import apprc as rc
    from apprc.definition.installation import (
        InstallationPlacement,
        InventoryEntry,
        MigrationInventory,
    )
    from apprc.definition.paths import Layout, ResourceKind
    from apprc.user_files.app_home.writes import file_revision

    root, environment, state = consumer
    installed = _run(
        _install_command(root, "--layout", "native"),
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr

    executable = Path(environment["UV_TOOL_BIN_DIR"]) / "lifecycle_consumer"
    for command in (("config", "init"), ("appdata", "init")):
        initialized = _run(
            [str(executable), *command],
            cwd=tmp_path,
            env=environment,
        )
        assert initialized.returncode == 0, initialized.stdout + initialized.stderr

    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    app_id = project["tool"]["apprc"]["distribution"]["app-id"]
    manager = rc.AppRC(
        app_id=app_id,
        paths=rc.Paths(config=True, appdata=True),
    ).installation(environment=environment)
    inspection = manager.inspect()
    record = inspection.record
    assert record is not None
    assert record.status == "ready"
    source_roots: dict[ResourceKind, Path | None] = {
        "config": record.placement.config_dir,
        "appdata": record.placement.appdata_dir,
    }
    assert all(path is not None for path in source_roots.values())
    appdata_root = source_roots["appdata"]
    assert appdata_root is not None
    payload = appdata_root / "migration-payload.bin"
    payload.write_bytes(b"preserve this application data")

    destination_root = tmp_path / "migrated resources"
    destinations: list[Path] = []
    entries: list[InventoryEntry] = []
    for kind, source_root in source_roots.items():
        assert source_root is not None
        assert source_root.is_dir()
        for source in sorted(source_root.rglob("*")):
            if source.is_dir():
                continue
            assert source.is_file() and not source.is_symlink()
            relative = source.relative_to(source_root)
            destination = destination_root / kind / relative
            entries.append(InventoryEntry(source, "file", file_revision(source), kind))
            destinations.append(destination)
    assert any(entry.path.name == ".apprc-owner.json" for entry in entries)
    assert payload in {entry.path for entry in entries}
    owner_marker_contents = {
        kind: (source_root / ".apprc-owner.json").read_bytes()
        for kind, source_root in source_roots.items()
        if source_root is not None
    }
    placement = InstallationPlacement(
        Layout.single_root(destination_root),
        config_dir=destination_root / "config",
        appdata_dir=destination_root / "appdata",
        capabilities=record.placement.capabilities,
    )
    inventory = MigrationInventory(
        tmp_path,
        destination_root,
        tuple(entries),
        tuple(destinations),
    )
    plan = manager.plan_migration(
        placement,
        inventory=inventory,
        quiescent=True,
    )
    original_rename = Path.rename

    def interrupt_after_payload_move(source: Path, destination: Path) -> Path:
        moved = original_rename(source, destination)
        if source == payload:
            raise RuntimeError("simulated interruption after resource move")
        return moved

    monkeypatch.setattr(Path, "rename", interrupt_after_payload_move)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        manager.migrate(plan, quiescent=True)
    monkeypatch.setattr(Path, "rename", original_rename)

    pending = manager.inspect()
    assert pending.status == "incomplete"
    assert pending.record is not None and pending.record.operation is not None
    assert pending.record.operation.kind == "migrate"
    assert pending.record.migration is not None
    assert pending.record.migration.phase == "staged"
    assert pending.revision is not None
    unknown = appdata_root / "unlisted-user-content.txt"
    unknown.write_text("leave unlisted content untouched", encoding="utf-8")

    resumed = _run(
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
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr

    final = manager.inspect()
    assert final.status == "ready"
    assert final.record is not None
    assert final.record.operation is None
    assert final.record.migration is not None
    assert final.record.migration.phase == "activated"
    assert final.record.placement == placement
    assert final.record.current is not None
    assert final.record.current.placement == placement
    assert (destination_root / "appdata" / payload.name).read_bytes() == (
        b"preserve this application data"
    )
    assert (
        destination_root / "appdata" / ".apprc-owner.json"
    ).read_bytes() == owner_marker_contents["appdata"]
    assert (
        destination_root / "config" / ".apprc-owner.json"
    ).read_bytes() == owner_marker_contents["config"]
    assert unknown.read_text(encoding="utf-8") == "leave unlisted content untouched"
