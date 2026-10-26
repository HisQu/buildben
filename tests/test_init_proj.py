"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Generator
from pathlib import Path

import pytest


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    """Run a command, and show stdout/stderr if it fails."""
    try:
        subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        msg = (
            "Command failed.\n"
            f"CMD: {cmd}\n"
            f"CWD: {cwd}\n"
            f"EXIT: {e.returncode}\n"
            f"STDOUT:\n{e.stdout}\n"
            f"STDERR:\n{e.stderr}\n"
        )
        raise AssertionError(msg) from e


def _project_env(project_root: Path) -> dict[str, str]:
    """Return an environment that can import buildben and a generated package.

    :param project_root: Generated project root.
    :return: Subprocess environment with local ``src`` paths prepended.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BUBE_TEST_TMP_")
    }
    repo_src = Path(__file__).resolve().parents[1] / "src"
    src_paths = [str(repo_src), str(project_root / "src")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        src_paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(src_paths)
    env["BUBE_TEST_TMP_APPRC_DIR"] = str(project_root / ".test-config")
    return env


def _git_output(project_root: Path, *args: str) -> str:
    """Run Git in a temporary scaffold project and return standard output.

    :param project_root: Git repository root.
    :param args: Git command arguments after ``git``.
    :return: Stripped standard output.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def _initialize_worktree_test_repo(project_root: Path) -> str:
    """Commit a generated project on ``main`` for worktree recipe checks.

    :param project_root: Generated project root.
    :return: Initial commit SHA.
    """
    env = _project_env(project_root)
    for args in (
        ["git", "init", "--initial-branch=main"],
        ["git", "config", "user.name", "Buildben scaffold test"],
        ["git", "config", "user.email", "buildben-test@example.invalid"],
        ["git", "add", "--all"],
        ["git", "commit", "-m", "Initialize generated project"],
    ):
        _run(args, cwd=project_root, env=env)
    return _git_output(project_root, "rev-parse", "HEAD")


def _worktree_recipe_env(
    project_root: Path,
    tmp_path: Path,
    *,
    uv_status: int = 0,
) -> tuple[dict[str, str], Path]:
    """Mock the optional uv sync through Bash's startup hook without PATH edits.

    :param project_root: Generated project root.
    :param tmp_path: Temporary directory for the call log and hook.
    :param uv_status: Status returned by the mocked uv command.
    :return: Recipe environment and uv call log path.
    """
    bash_env = tmp_path / "worktree-test-bash-env"
    bash_env.write_text(
        "uv() {\n"
        '  printf \'%s\\n\' "$PWD" "${UV_PROJECT_ENVIRONMENT-}" "$*" >> "$WORKTREE_TEST_UV_LOG"\n'
        '  return "${WORKTREE_TEST_UV_STATUS:-0}"\n'
        "}\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "worktree-test-uv.log"
    env = _project_env(project_root)
    env["BASH_ENV"] = str(bash_env)
    env["WORKTREE_TEST_UV_LOG"] = str(log_path)
    env["WORKTREE_TEST_UV_STATUS"] = str(uv_status)
    env["UV_PROJECT_ENVIRONMENT"] = str(tmp_path / "other-checkout" / ".venv")
    return env, log_path


def _run_just_recipe(
    project_root: Path,
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Run a generated just recipe and retain its output for assertions.

    :param project_root: Generated project root.
    :param env: Child-process environment.
    :param args: Recipe name followed by its arguments.
    :return: Captured just process result.
    """
    return subprocess.run(
        ["just", "--no-dotenv", "--justfile", str(project_root / "justfile"), *args],
        cwd=project_root,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


@pytest.fixture()
def bube_test_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Path, None, None]:
    """Create a scaffolded project named 'bube_test_tmp' and remove it later."""
    # == Import the real scaffolder =============================================
    import buildben.init_proj as scaffolder

    # -- Make the test non-interactive -----------------------------------------
    # > If warn_dir_overwrite ever prompts, CI will hang.
    monkeypatch.setattr(scaffolder.utils, "warn_dir_overwrite", lambda _p: None)

    # -- Scaffold ---------------------------------------------------------------
    args = argparse.Namespace(
        name="bube_test_tmp",
        target_dir=str(tmp_path),
        git_init=False,
        github_user="github-user",
    )
    scaffolder._run(args)

    proot = tmp_path / "bube_test_tmp"
    try:
        yield proot
    finally:
        shutil.rmtree(proot, ignore_errors=True)


def test_scaffolded_project_runs_pytest(bube_test_project: Path) -> None:
    """Run pytest inside the generated project."""
    proot = bube_test_project
    proj_name = "bube_test_tmp"

    # == Compile generated modules and run their package tests
    _run(
        [sys.executable, "-m", "compileall", "-q", str(proot / "src" / proj_name)],
        cwd=proot,
        env=_project_env(proot),
    )
    _run([sys.executable, "-m", "pytest", "-q"], cwd=proot, env=_project_env(proot))


def test_scaffolded_release_publisher_runs_without_buildben_installed(
    bube_test_project: Path,
) -> None:
    """Run the generated release publisher without site-packages or BuildBen."""
    project_root = bube_test_project
    package = "bube_test_tmp_dev"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    result = subprocess.run(
        [sys.executable, "-S", "-m", f"{package}.packaging.release_assets", "--help"],
        cwd=project_root,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _runtime_command(project_root: Path, *arguments: str) -> str:
    """Run the generated CLI with isolated configuration files.

    :param project_root: Generated project containing the source package.
    :param arguments: Arguments for the generated module entry point.
    :return: Standard output after a successful command.
    """
    result = subprocess.run(
        [sys.executable, "-m", "bube_test_tmp", *arguments],
        cwd=project_root,
        env=_project_env(project_root),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_scaffolded_project_runs_apprc_configuration(bube_test_project: Path) -> None:
    """Exercise generated AppRC commands, cleanup safety, and retained data."""
    proot = bube_test_project
    assert "appdata" in _runtime_command(proot, "--help")
    paths = json.loads(_runtime_command(proot, "appdata", "paths", "--json"))
    assert paths["apprc_dir"] == str(proot / ".test-config")
    _runtime_command(proot, "appdata", "clean", "--dry-run")
    alternate_dir = proot / "alternate-apprc"
    alternate_paths = json.loads(
        _runtime_command(
            proot, "appdata", "paths", "--apprc-dir", str(alternate_dir), "--json"
        )
    )
    assert alternate_paths["apprc_dir"] == str(alternate_dir)
    _runtime_command(
        proot, "appdata", "clean", "--dry-run", "--apprc-dir", str(alternate_dir)
    )
    assert not (proot / ".test-config").exists()
    assert not alternate_dir.exists()
    assert "config" in _runtime_command(proot, "--help")
    _runtime_command(proot, "version")
    diagnose = json.loads(_runtime_command(proot, "diagnose", "--json"))
    assert diagnose["apprc_dir"] == str(proot / ".test-config")
    assert not (proot / ".test-config").exists()
    before = subprocess.run(
        [sys.executable, "-m", "bube_test_tmp", "config", "doctor"],
        cwd=proot,
        env=_project_env(proot),
        capture_output=True,
        check=False,
    )
    assert before.returncode == 1
    _runtime_command(
        proot, "config", "setup", "--yes", "--storage-root", str(proot / "storage")
    )
    _runtime_command(proot, "config", "doctor")
    initial = json.loads(_runtime_command(proot, "config", "show", "--json"))
    assert initial["config"]["message"] == "Hello from bube_test_tmp"
    _runtime_command(
        proot, "config", "set", "app.message", "Saved value", "--scope", "storage"
    )
    saved = json.loads(_runtime_command(proot, "config", "show", "--json"))
    assert saved["config"]["message"] == "Saved value"
    assert (proot / "storage" / "apprc.storage.env").is_file()
    assert (proot / ".test-config" / "apprc.toml").is_file()
    assert not (proot / ".test-config" / "apprc.user.env").exists()
    _runtime_command(
        proot, "config", "storage", "add", "work", str(proot / "work"), "--yes"
    )
    work = json.loads(
        _runtime_command(proot, "--storage", "work", "config", "show", "--json")
    )
    assert work["storage_name"] == "work"
    assert work["config"]["message"] == "Hello from bube_test_tmp"
    _runtime_command(proot, "config", "storage", "select", "work")
    assert (
        json.loads(_runtime_command(proot, "config", "show", "--json"))["storage_name"]
        == "work"
    )
    external_payload = proot / "storage" / "retained-payload"
    external_payload.write_text("retain external data\n", encoding="utf-8")
    _runtime_command(proot, "appdata", "clean", "--dry-run")
    _runtime_command(proot, "appdata", "clean", "--yes")
    assert external_payload.read_text(encoding="utf-8") == "retain external data\n"


def test_scaffolded_lifecycle_support_runs_from_generated_project(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Run generated lifecycle help and a no-write record preflight."""
    proot = bube_test_project
    distribution = proot / "src" / "bube_test_tmp_dev" / "distribution"
    lifecycle = distribution / "lifecycle.py"
    expected_files = [
        lifecycle,
        distribution / "uninstall.sh",
        distribution / "uninstall.cmd",
        distribution / "uninstall.ps1",
        proot / "uninstall.sh",
        proot / "uninstall.cmd",
    ]
    for path in expected_files:
        assert path.is_file(), path

    env = _project_env(proot)
    uv_path = shutil.which("uv")
    assert uv_path is not None
    base_python_result = subprocess.run(
        [
            uv_path,
            "python",
            "find",
            "--system",
            "--no-project",
            "--no-python-downloads",
        ],
        cwd=proot,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    assert base_python_result.returncode == 0, (
        base_python_result.stdout + base_python_result.stderr
    )
    base_python = base_python_result.stdout.strip()
    state_root = tmp_path / "generated lifecycle state"
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "LOCALAPPDATA": str(tmp_path / "local appdata"),
            "XDG_STATE_HOME": str(state_root),
            "UV_CACHE_DIR": str(tmp_path / "uv cache"),
            "UV_TOOL_BIN_DIR": str(tmp_path / "uv bin"),
            "UV_TOOL_DIR": str(tmp_path / "uv tools"),
        }
    )
    for directory in (Path(env["HOME"]), Path(env["LOCALAPPDATA"])):
        directory.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [base_python, "-S", str(lifecycle), "--help"],
        cwd=proot,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "record" in result.stdout
    result = subprocess.run(
        [
            base_python,
            "-S",
            str(lifecycle),
            "record",
            "--uv",
            uv_path,
            "--version",
            "0.1.0",
            "--source-ref",
            "a" * 40,
            "--check",
        ],
        cwd=proot,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    state_directory = (
        Path(env["LOCALAPPDATA"]) / "bube-test-tmp" / "installation"
        if os.name == "nt"
        else state_root / "bube-test-tmp" / "installation"
    )
    assert not state_directory.exists()
    if os.name != "nt":
        assert os.access(distribution / "uninstall.sh", os.X_OK)
        assert os.access(proot / "uninstall.sh", os.X_OK)


@pytest.mark.parametrize("failure", [None, "registry", "overlap", "child"])
def test_installed_generated_app_cleanup_lifecycle(
    bube_test_project: Path, tmp_path: Path, failure: str | None
) -> None:
    """Exercise real tool installation and saved native cleanup with safe failures."""
    project = bube_test_project
    settings_path = project / "src" / "bube_test_tmp" / "config" / "sections" / "app.py"
    with settings_path.open("a", encoding="utf-8") as stream:
        stream.write('\n    count: int = rc.field("BUBE_TEST_TMP_COUNT", default=1)\n')
    uv = shutil.which("uv")
    assert uv is not None
    env = _project_env(project)
    base = subprocess.run(
        [uv, "python", "find", "--system", "--no-project", "--no-python-downloads"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert base.returncode == 0, base.stdout + base.stderr
    base_python = base.stdout.strip()
    isolated = tmp_path / "installed consumer"
    state_root = isolated / "state"
    local_appdata = isolated / "local appdata"
    env.update(
        {
            "HOME": str(isolated / "home"),
            "XDG_CONFIG_HOME": str(isolated / "config"),
            "XDG_DATA_HOME": str(isolated / "data"),
            "XDG_STATE_HOME": str(state_root),
            "XDG_CACHE_HOME": str(isolated / "cache"),
            "LOCALAPPDATA": str(local_appdata),
            "UV_TOOL_DIR": str(isolated / "tools"),
            "UV_TOOL_BIN_DIR": str(isolated / "bin"),
            "UV_CACHE_DIR": str(isolated / "uv cache"),
            "BUBE_TEST_TMP_APPRC_DIR": str(isolated),
        }
    )
    env.pop("PYTHONPATH", None)
    for path in (Path(env["HOME"]), local_appdata):
        path.mkdir(parents=True, exist_ok=True)
    lifecycle = project / "src" / "bube_test_tmp_dev" / "distribution" / "lifecycle.py"
    record = [
        base_python,
        str(lifecycle),
        "record",
        "--uv",
        uv,
        "--version",
        "0.1.0",
        "--source-ref",
        "a" * 40,
    ]
    _run([*record, "--check"], cwd=project, env=env)
    _run(
        [uv, "tool", "install", "--python", base_python, str(project)],
        cwd=project,
        env=env,
    )
    _run(record, cwd=project, env=env)
    state_base = local_appdata if os.name == "nt" else state_root
    state = state_base / "bube-test-tmp" / "installation"
    receipt = json.loads((state / "receipt.json").read_text(encoding="utf-8"))
    tool_environment = Path(receipt["tool_dir"]) / "bube-test-tmp"
    command = Path(receipt["tool_bin_dir"]) / (
        "bube_test_tmp.exe" if os.name == "nt" else "bube_test_tmp"
    )
    tool_python = tool_environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    appdata = Path(env["BUBE_TEST_TMP_APPRC_DIR"])
    internal = appdata / "internal"
    external = tmp_path / "external retained storage"
    _run(
        [str(command), "config", "setup", "--yes", "--storage-root", str(internal)],
        cwd=project,
        env=env,
    )
    _run(
        [str(command), "config", "storage", "add", "external", str(external), "--yes"],
        cwd=project,
        env=env,
    )
    internal_payload = internal / "internal payload"
    external_payload = external / "external payload"
    unmanaged = appdata / "unmanaged"
    for path in (internal_payload, external_payload, unmanaged):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("retain unless managed internal\n", encoding="utf-8")
    env["BUBE_TEST_TMP_COUNT"] = "not-an-integer"
    invalid_runtime = subprocess.run(
        [str(command), "config", "show", "--json"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert invalid_runtime.returncode != 0
    _run([str(command), "appdata", "paths", "--json"], cwd=project, env=env)
    _run([str(command), "appdata", "clean", "--dry-run"], cwd=project, env=env)
    env.pop("BUBE_TEST_TMP_COUNT")
    if failure == "registry":
        (appdata / "apprc.toml").write_text("not valid = [", encoding="utf-8")
    elif failure == "overlap":
        _run(
            [
                str(command),
                "config",
                "storage",
                "add",
                "recovery",
                str(state.parent),
                "--yes",
            ],
            cwd=project,
            env=env,
        )
    elif failure == "child":
        location = subprocess.run(
            [
                str(tool_python),
                "-c",
                "from importlib import import_module; "
                "print(import_module('bube_test_tmp.cli.app').__file__)",
            ],
            cwd=project,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        cli_path = Path(location.stdout.strip())
        source = cli_path.read_text(encoding="utf-8")
        source = source.replace(
            "    app()\n",
            '    if "clean" in sys.argv and "--dry-run" not in sys.argv:\n'
            "        raise SystemExit(17)\n"
            "    app()\n",
        )
        cli_path.write_text(source, encoding="utf-8")
    env["BUBE_TEST_TMP_APPRC_DIR"] = str(tmp_path / "unselected appdata")
    launcher = (
        ["cmd.exe", "/d", "/c", str(state / "uninstall.cmd")]
        if os.name == "nt"
        else [str(state / "uninstall.sh")]
    )
    if failure is None:
        receipt_before = (state / "receipt.json").read_bytes()
        preview = subprocess.run(
            [
                *launcher,
                "--dry-run",
                "--clean-appdata",
                "--apprc-dir",
                str(appdata),
            ],
            cwd=project,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert preview.returncode == 0, preview.stdout + preview.stderr
        assert str(internal) in preview.stdout
        assert str(external) in preview.stdout
        assert internal_payload.read_text(encoding="utf-8") == (
            "retain unless managed internal\n"
        )
        assert command.is_file()
        assert tool_environment.is_dir()
        assert (state / "receipt.json").read_bytes() == receipt_before
    result = subprocess.run(
        [*launcher, "--clean-appdata", "--yes", "--apprc-dir", str(appdata)],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if failure is not None:
        assert result.returncode != 0, result.stdout + result.stderr
        assert command.is_file()
        assert tool_environment.is_dir()
        assert internal_payload.is_file()
        assert not json.loads((state / "receipt.json").read_text(encoding="utf-8"))[
            "package_removed"
        ]
        _run([*launcher, "--yes"], cwd=project, env=env)
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert not internal_payload.exists()
        assert not (appdata / "apprc.toml").exists()
    for retained in (external_payload, unmanaged):
        assert (
            retained.read_text(encoding="utf-8") == "retain unless managed internal\n"
        )
    assert not command.exists()
    assert not tool_environment.exists()
    assert (state / "lifecycle.py").is_file()
    assert json.loads((state / "receipt.json").read_text(encoding="utf-8"))[
        "package_removed"
    ]
    _run([*launcher, "--yes"], cwd=project, env=env)


def test_generated_python_passes_quality_checks(bube_test_project: Path) -> None:
    """Check generated imports and downstream use of AppRC's public types."""
    env = _project_env(bube_test_project)
    for command in (
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "pyright", "--pythonpath", sys.executable],
    ):
        _run(command, cwd=bube_test_project, env=env)


def test_buildben_help_hides_unimplemented_database_command() -> None:
    """Assert unfinished data scaffolding is not exposed in the public CLI."""
    result = subprocess.run(
        [sys.executable, "-m", "buildben.cli", "--help"],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=os.environ.copy(),
        check=True,
        text=True,
        capture_output=True,
    )

    assert "init-database" not in result.stdout
    assert "data" not in result.stdout


def test_scaffolded_worktree_create_handles_spaces_and_overrides_inherited_uv_env(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Create the worktree and sync uv into its own environment directory."""
    project_root = bube_test_project
    main_commit = _initialize_worktree_test_repo(project_root)
    env, uv_log = _worktree_recipe_env(project_root, tmp_path)
    inherited_environment = env["UV_PROJECT_ENVIRONMENT"]
    destination_parent = tmp_path / "worktree destinations"
    destination_parent.mkdir()
    destination = destination_parent / "parser trial"

    result = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        "feature/parser",
        str(destination),
        "main",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert _git_output(destination, "rev-parse", "HEAD") == main_commit
    assert _git_output(destination, "branch", "--show-current") == "feature/parser"
    assert uv_log.read_text(encoding="utf-8").splitlines() == [
        str(destination),
        str(destination / ".venv"),
        "sync --locked --all-extras --all-groups",
    ]
    assert env["UV_PROJECT_ENVIRONMENT"] == inherited_environment
    assert _git_output(project_root, "status", "--porcelain") == ""


def test_scaffolded_worktree_create_retains_checkout_when_uv_sync_fails(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Keep a created worktree available when dependency setup returns an error."""
    project_root = bube_test_project
    _initialize_worktree_test_repo(project_root)
    env, _uv_log = _worktree_recipe_env(project_root, tmp_path, uv_status=23)
    destination = tmp_path / "retained worktree"

    result = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        "feature/needs-inspection",
        str(destination),
        "main",
    )

    assert result.returncode == 23
    assert f"retained worktree for inspection: {destination}" in result.stderr
    assert destination.is_dir()
    assert (
        _git_output(destination, "branch", "--show-current")
        == "feature/needs-inspection"
    )


def test_scaffolded_worktree_create_rejects_shell_text_as_a_branch(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Reject invalid branch text without evaluating it as shell code."""
    project_root = bube_test_project
    _initialize_worktree_test_repo(project_root)
    env, _uv_log = _worktree_recipe_env(project_root, tmp_path)
    marker = tmp_path / "shell-injection-marker"
    destination = tmp_path / "should-not-exist"

    result = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        f"feature/$(touch {marker})",
        str(destination),
        "main",
    )

    assert result.returncode != 0
    assert "Invalid Git branch name." in result.stderr
    assert not marker.exists()
    assert not destination.exists()

    nested_destination = project_root / "nested worktree"
    path_result = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        "feature/nested",
        str(nested_destination),
        "main",
    )

    assert path_result.returncode != 0
    assert "outside every existing Git worktree" in path_result.stderr
    assert not nested_destination.exists()


def test_scaffolded_worktree_remove_refuses_main_dirty_and_unmerged_checkouts(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Refuse cleanup when it could discard the main, dirty, or unmerged worktree."""
    project_root = bube_test_project
    _initialize_worktree_test_repo(project_root)
    env, _uv_log = _worktree_recipe_env(project_root, tmp_path)

    main_result = _run_just_recipe(project_root, env, "worktree-remove", ".")
    assert main_result.returncode != 0
    assert "main worktree" in main_result.stderr

    destination = tmp_path / "feature checkout"
    created = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        "feature/unmerged",
        str(destination),
        "main",
    )
    assert created.returncode == 0, created.stdout + created.stderr

    (destination / "untracked.txt").write_text("keep me\n", encoding="utf-8")
    dirty_result = _run_just_recipe(
        project_root,
        env,
        "worktree-remove",
        str(destination),
    )
    assert dirty_result.returncode != 0
    assert "dirty worktree" in dirty_result.stderr
    assert destination.is_dir()

    (destination / "untracked.txt").unlink()
    (destination / "feature.txt").write_text("branch-only change\n", encoding="utf-8")
    _run(["git", "add", "feature.txt"], cwd=destination, env=env)
    _run(["git", "commit", "-m", "Add branch-only change"], cwd=destination, env=env)
    unmerged_result = _run_just_recipe(
        project_root,
        env,
        "worktree-remove",
        str(destination),
    )
    assert unmerged_result.returncode != 0
    assert "not merged into local main" in unmerged_result.stderr
    assert destination.is_dir()
    assert _git_output(destination, "branch", "--show-current") == "feature/unmerged"


def test_scaffolded_worktree_create_rejects_option_like_branch(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Validate local branch syntax before invoking worktree creation."""
    project_root = bube_test_project
    _initialize_worktree_test_repo(project_root)
    env, _uv_log = _worktree_recipe_env(project_root, tmp_path)
    destination = tmp_path / "invalid branch checkout"

    result = _run_just_recipe(
        project_root, env, "worktree-create", "-invalid", str(destination), "main"
    )

    assert result.returncode == 2
    assert "Invalid Git branch name." in result.stderr
    assert not destination.exists()


def test_scaffolded_worktree_remove_refuses_current_and_nested_checkouts(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Protect the calling checkout and registered worktrees nested in each other."""
    project_root = bube_test_project
    _initialize_worktree_test_repo(project_root)
    env, _uv_log = _worktree_recipe_env(project_root, tmp_path)
    destination = tmp_path / "outer checkout"
    _run(
        ["git", "worktree", "add", "-b", "feature/outer", str(destination), "main"],
        cwd=project_root,
        env=env,
    )
    current_result = _run_just_recipe(destination, env, "worktree-remove", ".")
    assert current_result.returncode == 2
    assert "current worktree" in current_result.stderr
    assert destination.is_dir()

    nested = destination / "nested checkout"
    _run(
        ["git", "worktree", "add", "-b", "feature/nested", str(nested), "main"],
        cwd=project_root,
        env=env,
    )
    # > Ignored nested files leave the outer checkout clean, exercising the guard.
    _run(
        [
            "git",
            "-C",
            str(destination),
            "config",
            "core.excludesFile",
            str(tmp_path / "nested-ignore"),
        ],
        cwd=project_root,
        env=env,
    )
    (tmp_path / "nested-ignore").write_text("nested checkout/\n", encoding="utf-8")
    assert _git_output(destination, "status", "--porcelain") == ""

    for selected in (destination, nested):
        result = _run_just_recipe(
            project_root, env, "worktree-remove", str(selected), "true"
        )
        assert result.returncode == 2
        assert "nested Git worktrees" in result.stderr
        assert destination.is_dir()
        assert nested.is_dir()
        assert _git_output(
            project_root, "show-ref", "--verify", "refs/heads/feature/outer"
        )
        assert _git_output(
            project_root, "show-ref", "--verify", "refs/heads/feature/nested"
        )


def test_scaffolded_worktree_remove_deletes_only_an_explicitly_selected_branch(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Keep branches by default and delete only the selected branch on request."""
    project_root = bube_test_project
    _initialize_worktree_test_repo(project_root)
    env, _uv_log = _worktree_recipe_env(project_root, tmp_path)
    _run(["git", "branch", "feature/unrelated"], cwd=project_root, env=env)

    retained_destination = tmp_path / "retained branch checkout"
    created = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        "feature/retained",
        str(retained_destination),
        "main",
    )
    assert created.returncode == 0, created.stdout + created.stderr
    removed = _run_just_recipe(
        project_root,
        env,
        "worktree-remove",
        str(retained_destination),
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not retained_destination.exists()
    assert _git_output(
        project_root, "show-ref", "--verify", "refs/heads/feature/retained"
    )

    deleted_destination = tmp_path / "deleted branch checkout"
    created = _run_just_recipe(
        project_root,
        env,
        "worktree-create",
        "feature/selected-for-deletion",
        str(deleted_destination),
        "main",
    )
    assert created.returncode == 0, created.stdout + created.stderr
    removed = _run_just_recipe(
        project_root,
        env,
        "worktree-remove",
        str(deleted_destination),
        "true",
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not deleted_destination.exists()
    assert _git_output(
        project_root, "show-ref", "--verify", "refs/heads/feature/unrelated"
    )
    remaining_branch = subprocess.run(
        [
            "git",
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/feature/selected-for-deletion",
        ],
        cwd=project_root,
        check=False,
        text=True,
        capture_output=True,
    )
    assert remaining_branch.returncode == 1


def test_scaffolded_project_includes_project_changelog(
    bube_test_project: Path,
) -> None:
    """Assert generated projects include a project-filled changelog."""
    changelog_path = bube_test_project / "CHANGELOG.md"

    assert changelog_path.is_file()

    changelog_text = changelog_path.read_text(encoding="utf-8")
    assert "bube_test_tmp" in changelog_text
    assert "0.1.0" in changelog_text
    assert "# [0.1.0] - " in changelog_text
    assert "[\\[0.1.0\\] - " in changelog_text
    assert "(#010---" in changelog_text
    assert "<my_project>" not in changelog_text
    assert "<project_name>" not in changelog_text
    assert "<initial_version>" not in changelog_text
    assert "<scaffold_date>" not in changelog_text
    assert "<bb_date>" not in changelog_text
    assert "<bb_today>" not in changelog_text
    assert "{my_project}" not in changelog_text
    assert "{project_name}" not in changelog_text
    assert "{initial_version}" not in changelog_text
    assert "{scaffold_date}" not in changelog_text
    assert "{bb_date}" not in changelog_text
    assert "{bb_today}" not in changelog_text


def test_scaffold_copy_preserves_active_pass_artifacts(tmp_path: Path) -> None:
    """Keep active pass artifacts unchanged when copying scaffold templates."""
    import buildben.init_proj as scaffolder

    project_root = tmp_path / "active project"
    project_root.mkdir()
    todo = project_root / "TODO.md"
    plan = project_root / "PLAN.md"
    todo_bytes = b"# Active pass\n\n- [ ] Complete the selected work\n"
    plan_bytes = b"# Plan\n\nComplete the selected work without losing tasks.\n"
    todo.write_bytes(todo_bytes)
    plan.write_bytes(plan_bytes)

    transfers = scaffolder._project_template_transfers(project_root, "sample_project")
    for destination in transfers.values():
        destination.parent.mkdir(parents=True, exist_ok=True)
    scaffolder.utils.copy_templates(
        transfers, Path(scaffolder.__file__).resolve().parent / "_templates_proj"
    )

    assert todo.read_bytes() == todo_bytes
    assert plan.read_bytes() == plan_bytes


def test_scaffolded_project_includes_project_backlog(
    bube_test_project: Path,
) -> None:
    """Generate a durable backlog without creating active pass artifacts."""
    assert (bube_test_project / "BACKLOG.md").is_file()
    assert not (bube_test_project / "TODO.md").exists()
    assert not (bube_test_project / "PLAN.md").exists()


def test_scaffolded_project_includes_typer_cli_scaffold(
    bube_test_project: Path,
) -> None:
    """Assert generated projects include the package-level Typer CLI scaffold."""
    proot = bube_test_project
    proj_name = "bube_test_tmp"
    package_root = proot / "src" / proj_name

    expected_files = [
        package_root / "main.py",
        package_root / "__main__.py",
        package_root / "cli" / "__init__.py",
        package_root / "cli" / "app.py",
    ]
    for expected_file in expected_files:
        assert expected_file.is_file(), expected_file

    generated_text = "\n\n".join(
        path.read_text(encoding="utf-8") for path in expected_files
    )
    for placeholder in (
        "{my_project}",
        "<my_project>",
        "{github_username}",
        "<github_username>",
    ):
        assert placeholder not in generated_text


def test_scaffolded_release_push_updates_main_and_tag_together(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Publish one prepared commit and its annotated tag to a test remote.

    :param bube_test_project: Generated project under test.
    :param tmp_path: Temporary parent for the bare Git remote.
    :return: None.
    """
    proot = bube_test_project
    env = _project_env(proot)
    remote = tmp_path / "release-remote.git"

    policy = subprocess.run(
        ["just", "--evaluate", "RELEASE_PYPI"],
        cwd=proot,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert policy.stdout == "false"

    _run(["git", "init", "--initial-branch", "main"], cwd=proot, env=env)
    _run(["git", "config", "user.email", "test@example.com"], cwd=proot, env=env)
    _run(["git", "config", "user.name", "Buildben Test"], cwd=proot, env=env)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=proot, env=env)
    _run(["git", "config", "tag.gpgsign", "false"], cwd=proot, env=env)
    _run(["git", "add", "."], cwd=proot, env=env)
    _run(["git", "commit", "-m", "Prepared release"], cwd=proot, env=env)
    _run(["git", "tag", "-a", "v0.1.0", "-m", "Release v0.1.0"], cwd=proot, env=env)
    _run(["git", "init", "--bare", str(remote)], cwd=tmp_path, env=env)
    _run(["git", "remote", "add", "origin", str(remote)], cwd=proot, env=env)

    missing_tag = subprocess.run(
        ["just", "release-push", "v0.1.1"],
        cwd=proot,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert missing_tag.returncode != 0
    assert "Annotated local tag v0.1.1 does not exist" in missing_tag.stderr

    release_push = subprocess.run(
        ["just", "--set", "RELEASE_PYPI", "true", "release-push", "v0.1.0"],
        cwd=proot,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "PyPI publication is disabled by RELEASE_PYPI" in release_push.stdout
    assert "publish-pypi" not in release_push.stdout
    _run(
        ["git", "--git-dir", str(remote), "show-ref", "--verify", "refs/heads/main"],
        cwd=tmp_path,
        env=env,
    )
    _run(
        ["git", "--git-dir", str(remote), "show-ref", "--verify", "refs/tags/v0.1.0"],
        cwd=tmp_path,
        env=env,
    )


def test_scaffolded_publish_pypi_requires_both_committed_policies(
    bube_test_project: Path,
    tmp_path: Path,
) -> None:
    """Reject false committed policies before GitHub and preserve true publishing."""
    proot = bube_test_project
    env = _project_env(proot)
    _run(["git", "init", "--initial-branch", "main"], cwd=proot, env=env)
    _run(["git", "config", "user.email", "test@example.com"], cwd=proot, env=env)
    _run(["git", "config", "user.name", "Buildben Test"], cwd=proot, env=env)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=proot, env=env)
    _run(["git", "config", "tag.gpgsign", "false"], cwd=proot, env=env)
    _run(["git", "add", "."], cwd=proot, env=env)
    _run(
        ["git", "commit", "-m", "Prepared release with PyPI disabled"],
        cwd=proot,
        env=env,
    )
    _run(["git", "tag", "-a", "v0.1.0", "-m", "Release v0.1.0"], cwd=proot, env=env)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$PUBLISH_PYPI_GH_LOG"\n'
        'case "$1:$2" in\n'
        "  auth:status) exit 0 ;;\n"
        "  release:view)\n"
        '    if [[ "$*" == *"--json isDraft"* ]]; then printf \'false\\n\'; '
        'elif [[ "$*" == *"--json assets"* ]]; then printf \'1\\n\'; '
        "else exit 90; fi ;;\n"
        "  workflow:run) exit 0 ;;\n"
        "  *) exit 91 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    gh_log = tmp_path / "gh.log"
    gh_log.write_text("", encoding="utf-8")
    env["PATH"] = os.pathsep.join([str(fake_bin), env.get("PATH", "")])
    env["PUBLISH_PYPI_GH_LOG"] = str(gh_log)

    disabled = subprocess.run(
        [
            "just",
            "--set",
            "RELEASE_PYPI",
            "true",
            "publish-pypi",
            "v0.1.0",
        ],
        cwd=proot,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert disabled.returncode != 0
    assert "current committed justfile" in disabled.stderr
    assert gh_log.read_text(encoding="utf-8") == ""

    justfile = proot / "justfile"
    justfile.write_text(
        justfile.read_text(encoding="utf-8").replace(
            'RELEASE_PYPI := "false"',
            'RELEASE_PYPI := "true"',
            1,
        ),
        encoding="utf-8",
    )
    _run(["git", "add", "justfile"], cwd=proot, env=env)
    _run(["git", "commit", "-m", "Enable committed PyPI policy"], cwd=proot, env=env)
    _run(["git", "branch", "v0.1.0", "HEAD"], cwd=proot, env=env)

    target_disabled = subprocess.run(
        ["just", "publish-pypi", "v0.1.0"],
        cwd=proot,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert target_disabled.returncode != 0
    assert "tag v0.1.0's committed justfile" in target_disabled.stderr
    assert gh_log.read_text(encoding="utf-8") == ""

    _run(["git", "tag", "-d", "v0.1.0"], cwd=proot, env=env)
    missing_exact_tag = subprocess.run(
        ["just", "publish-pypi", "v0.1.0"],
        cwd=proot,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert missing_exact_tag.returncode != 0
    assert "Could not resolve exact release tag ref refs/tags/v0.1.0" in (
        missing_exact_tag.stderr
    )
    assert gh_log.read_text(encoding="utf-8") == ""

    _run(
        ["git", "tag", "-a", "v0.1.0", "-m", "Release v0.1.0"],
        cwd=proot,
        env=env,
    )
    _run(["just", "publish-pypi", "v0.1.0"], cwd=proot, env=env)
    gh_calls = gh_log.read_text(encoding="utf-8").splitlines()
    assert gh_calls == [
        "auth status",
        "release view v0.1.0 --json isDraft --jq .isDraft",
        'release view v0.1.0 --json assets --jq [.assets[].name | select(endswith(".whl"))] | length',
        'release view v0.1.0 --json assets --jq [.assets[].name | select(endswith(".tar.gz"))] | length',
        "workflow run release.yml --raw-field release_tag=v0.1.0",
    ]


def test_scaffolded_project_includes_docs_scaffold(bube_test_project: Path) -> None:
    """Exercise the generated documentation's own outline and navigation checks."""
    docs = bube_test_project / "docs"
    for filename in (
        "README.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "docs/README.md",
        "docs/Explanations.md",
        "docs/How-To-User-Guides.md",
        "docs/References.md",
        "docs/EXAMPLES.md",
        "docs/Development.md",
    ):
        assert (bube_test_project / filename).is_file()
    ET.parse(docs / "assets" / "docs-reading-map.svg")
    _run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_documentation.py"],
        cwd=bube_test_project,
        env=_project_env(bube_test_project),
    )


def test_scaffolded_project_includes_project_neutral_mermaid_templates(
    bube_test_project: Path,
) -> None:
    """Check generated Mermaid assets substitute project names and stay ignored.

    :param bube_test_project: Project generated for this test.
    :return: None.
    """
    assets = bube_test_project / "assets"
    flowchart = (assets / "flowchart.IGNORE.mmd").read_text(encoding="utf-8")
    class_diagram = (assets / "classdiagram.IGNORE.mmd").read_text(encoding="utf-8")
    gitignore = (bube_test_project / ".gitignore").read_text(encoding="utf-8")

    assert "bube_test_tmp" in flowchart
    assert "BubeTestTmp" in class_diagram
    assert "{my_project}" not in flowchart + class_diagram
    assert "{MyProject}" not in flowchart + class_diagram
    assert "Docker" not in flowchart + class_diagram
    assert "LLM" not in flowchart + class_diagram
    assert "*.IGNORE*" in gitignore


@pytest.mark.parametrize("defect", ["group", "indent", "spacer"])
def test_scaffolded_documentation_rejects_outline_errors(
    bube_test_project: Path, defect: str
) -> None:
    """Prove generated CI rejects missing groups, nesting, and spacing.

    :param bube_test_project: Disposable rendered project.
    :param defect: One deliberate documentation-rule violation.
    :return: None.
    """
    page = bube_test_project / "docs" / "README.md"
    source = page.read_text(encoding="utf-8")
    replacements = {
        "group": ("# Find the right page\n", ""),
        "indent": ("  - [Start here](#start-here)", "- [Start here](#start-here)"),
        "spacer": ("<br>\n\n# Find the right page", "# Find the right page"),
    }
    original, broken = replacements[defect]
    assert original in source
    page.write_text(source.replace(original, broken, 1), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_documentation.py"],
        cwd=bube_test_project,
        env=_project_env(bube_test_project),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("page", "href"),
    [
        ("README.md", "missing-contributor-guide.md"),
        ("CONTRIBUTING.md", "docs/Development.md#missing-section"),
    ],
)
def test_scaffolded_documentation_rejects_broken_navigation(
    bube_test_project: Path, page: str, href: str
) -> None:
    """Prove generated checks reject missing files and section destinations.

    :param bube_test_project: Disposable generated project.
    :param page: Root document to give a broken link.
    :param href: Missing local destination.
    :return: None.
    """
    path = bube_test_project / page
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n[Missing destination]({href})\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_documentation.py",
            "-k",
            "documentation_links",
        ],
        cwd=bube_test_project,
        env=_project_env(bube_test_project),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert href in result.stdout + result.stderr


def test_scaffolded_documentation_ignores_example_links(
    bube_test_project: Path,
) -> None:
    """Allow illustrative broken links in hidden or fenced examples.

    :param bube_test_project: Disposable generated project.
    :return: None.
    """
    path = bube_test_project / "CONTRIBUTING.md"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n<!-- [Example](missing-example.md) -->\n"
            "\n```markdown\n[Example](docs/Development.md#missing-section)\n```\n"
        )
    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_documentation.py",
            "-k",
            "documentation_links",
        ],
        cwd=bube_test_project,
        env=_project_env(bube_test_project),
    )


@pytest.mark.parametrize(
    "title", ["User preferences and storage", "Several config sections"]
)
def test_generated_documentation_examples(bube_test_project: Path, title: str) -> None:
    """Run the complete source files printed in the generated Examples page."""
    proot = bube_test_project
    examples = (proot / "docs" / "EXAMPLES.md").read_text()
    section = examples.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0]
    files = re.findall(
        r"<!-- example-file: ([^\n]+) -->\s*```[^\n]*\n(.*?)^```",
        section,
        re.MULTILINE | re.DOTALL,
    )
    assert files
    for name, code in files:
        path = proot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)
    _runtime_command(
        proot, "config", "setup", "--yes", "--storage-root", str(proot / "data")
    )
    if title == "User preferences and storage":
        _runtime_command(
            proot,
            "config",
            "set",
            "app.message",
            "Shared preference",
            "--scope",
            "user",
        )
        assert (
            json.loads(_runtime_command(proot, "config", "show", "--json"))["config"][
                "message"
            ]
            == "Shared preference"
        )
        _runtime_command(
            proot,
            "config",
            "set",
            "app.message",
            "This storage only",
            "--scope",
            "storage",
        )
        assert (
            json.loads(_runtime_command(proot, "config", "show", "--json"))["config"][
                "message"
            ]
            == "This storage only"
        )
    else:
        _runtime_command(
            proot, "config", "set", "client.timeout", "10", "--scope", "storage"
        )
        result = subprocess.run(
            [sys.executable, "read_sections.py"],
            cwd=proot,
            env=_project_env(proot),
            text=True,
            capture_output=True,
            check=True,
        )
        assert result.stdout.splitlines() == ["Hello from bube_test_tmp", "10"]


def test_scaffolded_project_builds_without_missing_readme_warning(
    bube_test_project: Path,
) -> None:
    """Assert generated package metadata points at an existing README."""
    result = subprocess.run(
        ["uv", "build", "--no-sources"],
        cwd=str(bube_test_project),
        env=_project_env(bube_test_project),
        check=True,
        text=True,
        capture_output=True,
    )
    combined_output = f"{result.stdout}\n{result.stderr}"

    assert "README.md' cannot be found" not in combined_output
    assert "standard file not found" not in combined_output


def test_experiment_scaffold_is_minimal_and_runnable(
    bube_test_project: Path,
) -> None:
    """Assert generated experiment files compile and have no stale placeholders."""
    proot = bube_test_project
    env = _project_env(proot)
    _run(
        [sys.executable, "-m", "buildben.cli", "add-experim", "smoke"],
        cwd=proot,
        env=env,
    )

    experiment_root = next((proot / "experiments").glob("*_smoke"))
    python_files = [
        experiment_root / "run.py",
        experiment_root / "scripts" / "exp.py",
        experiment_root / "scripts" / "eval.py",
    ]
    all_generated_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*python_files, experiment_root / "REPORT.md"]
    )

    assert "<" not in all_generated_text
    assert "{experiment" not in all_generated_text
    assert "from bube_test_tmp import env" not in all_generated_text
    assert "import numpy" not in all_generated_text
    assert "import pandas" not in all_generated_text

    for python_file in python_files:
        _run([sys.executable, "-m", "py_compile", str(python_file)], cwd=proot, env=env)
        _run([sys.executable, str(python_file)], cwd=proot, env=env)


def test_env_snapshot_requires_experiment_dir() -> None:
    """Assert missing env-snapshot arguments fail without a traceback."""
    result = subprocess.run(
        [sys.executable, "-m", "buildben.cli", "env-snapshot"],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=os.environ.copy(),
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "experiment_dir" in result.stderr
    assert "Traceback" not in result.stderr


def test_env_snapshot_writes_uv_snapshot_outputs(bube_test_project: Path) -> None:
    """Assert env-snapshot writes reproducibility files using uv."""
    proot = bube_test_project
    env = _project_env(proot)

    _run(["uv", "lock"], cwd=proot, env=env)
    _run(["git", "init", "--initial-branch", "main"], cwd=proot, env=env)
    _run(["git", "config", "user.email", "test@example.com"], cwd=proot, env=env)
    _run(["git", "config", "user.name", "Buildben Test"], cwd=proot, env=env)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=proot, env=env)
    _run(["git", "config", "tag.gpgsign", "false"], cwd=proot, env=env)
    _run(["git", "add", "."], cwd=proot, env=env)
    _run(["git", "commit", "-m", "Initial generated project"], cwd=proot, env=env)

    _run(
        [sys.executable, "-m", "buildben.cli", "env-snapshot", "experiments/smoke"],
        cwd=proot,
        env=env,
    )

    snapshot_root = proot / "experiments" / "smoke"
    setup_dir = snapshot_root / "_setup"
    env_text = (snapshot_root / "experiment.env").read_text(encoding="utf-8")

    assert (setup_dir / "requirements.lock").is_file()
    assert any(setup_dir.glob("*.whl"))
    assert any(setup_dir.glob("*.tar.gz"))
    assert "COMMIT_HASH=" in env_text
    assert "LOCK_FILE=experiments/smoke/_setup/requirements.lock" in env_text
