"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import os
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile
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


def _assert_release_banner(recipe: str) -> None:
    """Protect the established visual treatment of prepared releases.

    :param recipe: Complete justfile text.
    :return: None.
    """
    banner = '''    echo "================================================================="
    echo "✅  RELEASE ${tag} PREPARED LOCALLY"
    echo "================================================================="
    echo
    echo "Nothing has been uploaded."
    echo
    echo "NEXT COMMAND, THIS STARTS THE RELEASE:"
    echo
    echo "  just release-push ${tag}"
    echo
    echo "GitHub will run CI, validate wheel and sdist artifacts, and create"
    echo "the GitHub Release. PyPI follows RELEASE_PYPI in the tagged justfile."
    echo "================================================================="'''
    assert banner in recipe


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
    reason="Install the local AppRC 0.25 wheels to verify generated runtime behavior.",
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
    reason="Install the local AppRC wheels to type-check a generated consumer.",
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
    assert "release-check:" in justfile_text
    assert "_release-artifact-check" in justfile_text
    assert "uv build --python 3.12 --no-sources --no-build-logs" in justfile_text
    assert 'twine check "$wheel" "$sdist"' in justfile_text
    assert "uv version --bump" in justfile_text
    assert 'RELEASE_PYPI := "false"' in justfile_text
    assert "PUBLISH_PYPI" not in justfile_text
    assert "uv publish --token" not in justfile_text
    _assert_release_banner(justfile_text)
    assert 'release-prepare level="patch":' in justfile_text
    assert "release-push tag:" in justfile_text
    assert "publish-pypi tag:" in justfile_text
    assert 'git push --atomic origin main "$tag"' in justfile_text
    assert "--all-extras --all-groups" in justfile_text

    readme_text = (proot / "README.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    development_text = (proot / "docs" / "Development.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[rag]"' in development_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in development_text
    assert "bube_test_tmp version" in readme_text
    assert "bube_test_tmp diagnose" in readme_text
    assert "bube_test_tmp config setup --yes --storage-root" in readme_text
    assert "bube_test_tmp config doctor" in readme_text
    assert (
        'bube_test_tmp config set app.message "Hello local storage" --scope storage'
        in readme_text
    )


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


def test_scaffolded_project_includes_project_todo(
    bube_test_project: Path,
) -> None:
    """Assert generated projects include the root TODO parking lot."""
    todo_path = bube_test_project / "TODO.md"

    assert todo_path.is_file()

    todo_text = todo_path.read_text(encoding="utf-8")
    assert "# Todo list" in todo_text
    assert "parking lot for actionable problems" in todo_text
    assert "CHANGELOG.md" in todo_text


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


def test_scaffolded_project_includes_release_workflow(
    bube_test_project: Path,
) -> None:
    """Assert generated repositories receive the active release contract."""
    ci = bube_test_project / ".github" / "workflows" / "ci.yml"
    release = bube_test_project / ".github" / "workflows" / "release.yml"
    release_notes = (
        bube_test_project
        / "src"
        / "bube_test_tmp_dev"
        / "packaging"
        / "release_notes.py"
    )
    smoke = release_notes.with_name("install_smoke.py")
    starter_test = bube_test_project / "tests" / "test_bube_test_tmp_package.py"

    for path in (ci, release, release_notes, smoke, starter_test):
        assert path.is_file(), path

    assert "workflow_call" in ci.read_text(encoding="utf-8")
    assert "uv sync --locked --all-extras --all-groups" in ci.read_text(
        encoding="utf-8"
    )
    release_text = release.read_text(encoding="utf-8")
    assert "github-release" in release_text
    assert "workflow_dispatch:" in release_text
    assert "release_tag:" in release_text
    assert "just --evaluate RELEASE_PYPI" in release_text
    assert "PUBLISH_PYPI" not in release_text
    assert "trusted-publishing" in release_text
    assert "publish-existing-release:" in release_text
    assert "needs.build.outputs.release_pypi == 'true'" in release_text
    assert release_text.count("if: github.event_name == 'push'") == 3
    assert "if: github.event_name == 'workflow_dispatch'" in release_text
    assert "gh release download" in release_text
    assert "--check-url" in release_text
    assert "actions/upload-artifact@v7" in release_text
    assert release_text.count("actions/download-artifact@v8") == 2

    manual_publish = release_text.split("  publish-existing-release:\n", 1)[1]
    assert "actions/checkout" not in manual_publish
    assert "uv build" not in manual_publish
    assert "environment: pypi" in manual_publish
    assert "id-token: write" in manual_publish

    development_text = (bube_test_project / "docs" / "Development.md").read_text(
        encoding="utf-8"
    )
    assert "just release-check" in development_text
    assert 'RELEASE_PYPI := "true"' in development_text
    assert "just release-prepare patch" in development_text
    assert "just release-push vMAJOR.MINOR.PATCH" in development_text
    assert "just publish-pypi vMAJOR.MINOR.PATCH" in development_text
    assert "PUBLISH_PYPI" not in development_text
    assert "just lock" in development_text

    release_notes_output = bube_test_project / "release-notes.md"
    _run(
        [
            sys.executable,
            str(release_notes),
            "0.1.0",
            "--output",
            str(release_notes_output),
        ],
        cwd=bube_test_project,
        env=_project_env(bube_test_project),
    )
    assert release_notes_output.read_text(encoding="utf-8").startswith("## ➕ Added")
    smoke_text = smoke.read_text(encoding="utf-8")
    assert "InstallSnapshot" in smoke_text
    assert "validate_install_snapshot" in smoke_text


def test_buildben_release_recipe_keeps_checks_visible_and_builds_quiet() -> None:
    """Assert the local release recipe retains useful status and safety output."""
    recipe = (Path(__file__).resolve().parents[1] / "justfile").read_text(
        encoding="utf-8"
    )

    assert "uv build --python 3.12 --no-sources --no-build-logs" in recipe
    assert "Python {{version}}: checks passed." in recipe
    assert "Version commit succeeded, but tag creation failed." in recipe
    _assert_release_banner(recipe)
    assert 'RELEASE_PYPI := "false"' in recipe
    assert 'release-prepare level="patch":' in recipe
    assert "release-push tag:" in recipe
    assert "publish-pypi tag:" in recipe
    assert 'git push --atomic origin main "$tag"' in recipe
    assert "PUBLISH_PYPI" not in recipe


def test_buildben_release_workflow_supports_policy_and_recovery() -> None:
    """Check the repository workflow against the current release contract.

    :return: None.
    """
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "just --evaluate RELEASE_PYPI" in workflow
    assert "needs.build.outputs.release_pypi == 'true'" in workflow
    assert "PUBLISH_PYPI" not in workflow
    assert "publish-existing-release:" in workflow
    assert workflow.count("if: github.event_name == 'push'") == 3
    assert "if: github.event_name == 'workflow_dispatch'" in workflow
    assert "--check-url https://pypi.org/simple/buildben/" in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert workflow.count("actions/download-artifact@v8") == 2

    manual_publish = workflow.split("  publish-existing-release:\n", 1)[1]
    assert "actions/checkout" not in manual_publish
    assert "uv build" not in manual_publish
    assert "gh release download" in manual_publish
    assert "uv publish" in manual_publish


def test_buildben_ci_installs_just_for_release_recipe_tests() -> None:
    """Require the command used by release integration tests in CI.

    :return: None.
    """
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "extractions/setup-just@v4" in workflow
    assert 'just-version: "1.56.0"' in workflow


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

    _run(["just", "release-push", "v0.1.0"], cwd=proot, env=env)
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


def _markdown_anchors(text: str) -> set[str]:
    """Collect heading anchors and explicit anchors outside code blocks.

    :param text: Markdown source.
    :return: GitHub-style local anchor names.
    """
    text = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", text, flags=re.M | re.S)
    result = set(re.findall(r'<a\s+id="([^"]+)"', text))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.M):
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
            r"^```[^\n]*\n.*?^```\s*$", "", path.read_text(), flags=re.M | re.S
        )
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
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
    reason="Install the local AppRC 0.25 wheels to execute the generated documentation.",
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
        r"<!-- example-file: ([^\n]+) -->\s*```[^\n]*\n(.*?)^```", section, re.M | re.S
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


def test_buildben_wheel_includes_all_template_assets(tmp_path: Path) -> None:
    """Assert installed wheels contain every scaffold template kind."""
    repo_root = Path(__file__).resolve().parents[1]
    _run(
        ["uv", "build", "--out-dir", str(tmp_path), "--no-sources"],
        cwd=repo_root,
        env=os.environ.copy(),
    )

    wheel_path = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())

    assert "buildben/_templates_experim/_REPORT.md" in names
    assert "buildben/_templates_experim/_paths.env" in names
    assert "buildben/_templates_experim/_run.py.tmpl" in names
    assert "buildben/_templates_proj/_CHANGELOG.md" in names
    assert "buildben/_templates_proj/_TODO.md" in names
    assert "buildben/_templates_proj/_src-cli-app.py.tmpl" in names
    assert "buildben/_templates_proj/_tests-test_documentation.py.tmpl" in names
    assert "buildben/_templates_proj/_github-release.yml" in names
    assert "buildben/_templates_proj/_src-dev-packaging-release_notes.py.tmpl" in names


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
