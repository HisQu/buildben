"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Generator
from pathlib import Path
from urllib.parse import unquote, urlsplit

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


@pytest.mark.skipif(
    importlib.util.find_spec("apprc") is None,
    reason="Install AppRC >=0.25.0,<0.26 to verify generated runtime behavior.",
)
def test_scaffolded_project_runs_apprc_configuration(bube_test_project: Path) -> None:
    """Exercise setup, storage edits, precedence, and named storage selection."""
    proot = bube_test_project
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


@pytest.mark.skipif(
    importlib.util.find_spec("apprc") is None,
    reason="Install AppRC >=0.25.0,<0.26 to type-check a generated consumer.",
)
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


def test_scaffolded_project_uses_dependency_group_template(
    bube_test_project: Path,
) -> None:
    """Assert generated dependency docs and commands match the template policy."""
    proot = bube_test_project

    pyproject_path = proot / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)

    project = pyproject["project"]
    assert project["readme"] == "README.md"
    assert project["dependencies"] == [
        "apprc>=0.25.0,<0.26",
        "typer",
    ]
    assert "python-dotenv" not in project["dependencies"]
    assert project["scripts"] == {"bube_test_tmp": "bube_test_tmp.main:main"}

    optional_dependencies = project.get("optional-dependencies", {})
    assert "dev" not in optional_dependencies
    assert "# [project.optional-dependencies]" in pyproject_text
    assert "# rag = [" in pyproject_text

    dependency_groups = pyproject["dependency-groups"]
    assert {"pytest>=8.2", "pyright>=1.1", "ruff>=0.4"} <= set(dependency_groups["dev"])

    package_data = pyproject["tool"]["setuptools"]["package-data"]["*"]
    assert "config/apprc.defaults.env" in package_data

    envrc_text = (proot / ".envrc").read_text(encoding="utf-8")
    assert "--all-extras" in envrc_text
    assert "--all-groups" in envrc_text
    assert "--no-default-groups" in envrc_text
    assert "uv sync --frozen --all-extras --all-groups" in envrc_text

    justfile_text = (proot / "justfile").read_text(encoding="utf-8")
    assert "alias install := sync" in justfile_text
    assert "uv sync --all-extras --all-groups --locked" in justfile_text
    assert "uv sync --frozen --all-extras --all-groups" in justfile_text
    assert "uv sync --check --all-extras --all-groups" in justfile_text
    assert "uv lock" in justfile_text
    assert "_check-clean-worktree" in justfile_text
    assert "worktree-create branch destination base:" in justfile_text
    assert 'worktree-remove destination delete_branch="false":' in justfile_text
    assert "uv sync --locked --all-extras --all-groups" in justfile_text
    assert 'UV_PROJECT_ENVIRONMENT="$destination_path/.venv"' in justfile_text
    readme_text = (proot / "README.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    development_text = (proot / "docs" / "Development.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[rag]"' in development_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in development_text
    assert "just worktree-create feature/parser" in development_text
    assert 'just worktree-remove "../parser trial" true' in development_text
    assert "the normal project install paths" in development_text
    assert "above do not" in development_text
    assert "bube_test_tmp version" in readme_text
    assert "bube_test_tmp diagnose" in readme_text
    assert "bube_test_tmp config setup --yes --storage-root" in readme_text
    assert "bube_test_tmp config doctor" in readme_text
    assert (
        'bube_test_tmp config set app.message "Hello local storage" --scope storage'
        in readme_text
    )


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

    cli_text = (package_root / "cli" / "app.py").read_text(encoding="utf-8")
    main_text = (package_root / "main.py").read_text(encoding="utf-8")
    pyproject_text = (proot / "pyproject.toml").read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)

    assert "typer.Typer" in cli_text
    assert '@app.command("version")' in cli_text
    assert '@app.command("diagnose")' in cli_text
    assert "rc.cli.mount_config_cli" in cli_text
    assert "from bube_test_tmp.config.bundle import BubeTestTmpConfig" in cli_text
    assert "state.resolved" in cli_text
    assert "rc.cli.CliRuntimePolicy" in cli_text
    assert "rc.cli.RuntimeIndependentCommand" in cli_text
    assert "rc.cli.dump_json" in cli_text
    assert "APP_CONFIG.typer_app" not in cli_text
    assert "bootstrap_cli_env" not in cli_text
    assert "config_request_skips_runtime_bootstrap" not in cli_text
    assert "apprc.runtime_config" not in cli_text
    assert "apprc.logging" not in cli_text
    assert "logging.basicConfig" in cli_text
    assert "from bube_test_tmp.cli.app import main" in main_text
    assert pyproject["project"]["scripts"][proj_name] == f"{proj_name}.main:main"

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


def test_scaffolded_project_has_apprc_config_package(
    bube_test_project: Path,
) -> None:
    """Assert generated projects use AppRC instead of legacy dotenv helpers."""
    proot = bube_test_project
    package_root = proot / "src" / "bube_test_tmp"

    config_files = [
        "__init__.py",
        "app.py",
        "bundle.py",
        "apprc.defaults.env",
        "sections/__init__.py",
        "sections/app.py",
    ]
    config_root = package_root / "config"
    for name in config_files:
        assert (config_root / name).is_file(), name
    for obsolete in (
        "catalog.py",
        "_facade.py",
        "__init__.pyi",
        "sections/_facade.py",
        "sections/__init__.pyi",
        "owners.py",
        ".env.shared",
    ):
        assert not (config_root / obsolete).exists(), obsolete
    assert not (package_root / "paths.py").exists()
    assert not (package_root / "utils" / "path_resolver.py").exists()
    assert not (proot / ".env.template").exists()

    config_text = (config_root / "app.py").read_text(encoding="utf-8")
    section_text = (config_root / "sections" / "app.py").read_text(encoding="utf-8")
    bundle_text = (config_root / "bundle.py").read_text(encoding="utf-8")
    defaults_text = (config_root / "apprc.defaults.env").read_text(encoding="utf-8")
    agents_text = (proot / "AGENTS.md").read_text(encoding="utf-8")

    assert "APP_RC = rc.AppRC(" in config_text
    assert 'storage=rc.Storage(selector_env_key="BUBE_TEST_TMP_STORAGE")' in config_text
    assert 'command_name="bube_test_tmp"' in config_text
    assert "user_dotenv=" not in config_text
    assert "@APP_RC.config(" in section_text
    assert "class AppSettings(rc.Config):" in section_text
    assert 'rc_path=("app",)' in section_text
    assert 'prefix="BUBE_TEST_TMP_"' in section_text
    assert "@APP_RC.bundle" in bundle_text
    assert "class BubeTestTmpConfig:" in bundle_text
    assert "app: AppSettings" in bundle_text
    assert 'BUBE_TEST_TMP_MESSAGE="Hello from bube_test_tmp"' in defaults_text
    assert "bube_test_tmp.config" in agents_text
    assert "rc.cli.mount_config_cli" in agents_text
    assert "config.catalog" not in agents_text


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


def _markdown_anchors(text: str) -> set[str]:
    """Collect heading anchors and explicit anchors outside code blocks.

    :param text: Markdown source.
    :return: GitHub-style local anchor names.
    """
    text = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", text, flags=re.MULTILINE | re.DOTALL)
    result = set(re.findall(r'<a\s+id="([^"]+)"', text))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
        heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        result.add(f"{slug}-{count}" if count else slug)
        counts[slug] = count + 1
    return result


def test_scaffolded_project_includes_docs_scaffold(bube_test_project: Path) -> None:
    """Check rendered documentation names, file links, and section anchors."""
    labels = {
        "README.md": "Documentation",
        "Explanations.md": "Explanations",
        "How-To-User-Guides.md": "How-to user guides",
        "References.md": "References",
        "EXAMPLES.md": "Examples",
        "Development.md": "Development",
    }
    docs = bube_test_project / "docs"
    references = (docs / "References.md").read_text(encoding="utf-8")
    assert "How-To-User-Guides.md#install-from-a-cloned-repository" in references
    assert (bube_test_project / "tests" / "test_documentation.py").is_file()
    ET.parse(docs / "assets" / "docs-reading-map.svg")
    for filename, label in labels.items():
        text = (docs / filename).read_text()
        assert text.startswith(f"# {label}\n")
        assert "> Related:" not in text and "> Related links:" not in text
        assert "{my_project}" not in text and "{MyProject}" not in text
    paths = [
        bube_test_project / "README.md",
        bube_test_project / "AGENTS.md",
        *docs.glob("*.md"),
    ]
    errors: list[str] = []
    for path in paths:
        text = re.sub(
            r"^```[^\n]*\n.*?^```\s*$",
            "",
            path.read_text(),
            flags=re.MULTILINE | re.DOTALL,
        )
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        for label, href in re.findall(r"!?\[([^\]\n]*)\]\(([^\s)]+)\)", text):
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc:
                continue
            target = (
                (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            )
            if not target.exists():
                errors.append(f"{path.name}: missing {href}")
            elif parsed.fragment and target.suffix == ".md":
                if unquote(parsed.fragment) not in _markdown_anchors(
                    target.read_text()
                ):
                    errors.append(f"{path.name}: missing anchor {href}")
            elif target.parent == docs and target.name in labels:
                assert label == labels[target.name], (path, label, href)
    assert not errors, "\n".join(errors)


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


@pytest.mark.skipif(
    importlib.util.find_spec("apprc") is None,
    reason="Install AppRC >=0.25.0,<0.26 to execute the generated documentation.",
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
