"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile
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
    env = os.environ.copy()
    repo_src = Path(__file__).resolve().parents[1] / "src"
    src_paths = [str(repo_src), str(project_root / "src")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        src_paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(src_paths)
    env["XDG_CONFIG_HOME"] = str(project_root / ".test-config")
    return env


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

    # == Add runtime coverage to the generated package test =====================
    test_file = proot / "tests" / "test_generated_smoke.py"
    test_file.write_text(
        (
            "from __future__ import annotations\n"
            "import importlib.util\n"
            "import os\n"
            "import py_compile\n"
            "import subprocess\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "import pytest\n\n"
            "def _project_env(project_root: Path) -> dict[str, str]:\n"
            "    env = os.environ.copy()\n"
            "    src_dir = str(project_root / 'src')\n"
            "    env['PYTHONPATH'] = src_dir + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')\n"
            "    env['XDG_CONFIG_HOME'] = str(project_root / '.test-config')\n"
            "    return env\n\n"
            "def test_generated_sources_compile() -> None:\n"
            "    project_root = Path(__file__).resolve().parents[1]\n"
            f"    package_root = project_root / 'src' / '{proj_name}'\n"
            "    for relative in (\n"
            "        'main.py',\n"
            "        '__main__.py',\n"
            "        'cli/app.py',\n"
            "        'config/__init__.py',\n"
            "        'config/_facade.py',\n"
            "        'config/app.py',\n"
            "        'config/bundle.py',\n"
            "        'config/catalog.py',\n"
            "        'config/sections/__init__.py',\n"
            "        'config/sections/_facade.py',\n"
            "        'config/sections/app.py',\n"
            "    ):\n"
            "        py_compile.compile(package_root / relative, doraise=True)\n\n"
            "def test_cli_runtime_when_apprc_is_installed() -> None:\n"
            "    if importlib.util.find_spec('apprc') is None:\n"
            "        pytest.skip('Generated CLI runtime smoke test needs apprc installed.')\n"
            "    project_root = Path(__file__).resolve().parents[1]\n"
            "    env = _project_env(project_root)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', '--help'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', '--help'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'version'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'diagnose', '--json'], cwd=str(project_root), env=env, check=True)\n"
            f"    before = subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'doctor'], cwd=str(project_root), env=env, text=True, capture_output=True, check=False)\n"
            "    assert before.returncode == 1\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'setup', '--yes', '--storage-root', str(project_root / 'storage')], cwd=str(project_root), env=env, check=True)\n"
            f"    env['{proj_name.upper()}_STORAGE'] = str(project_root / 'storage')\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'doctor'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'show', '--json'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'set', 'app.message', 'Hello local storage', '--scope', 'storage'], cwd=str(project_root), env=env, check=True)\n"
        ),
        encoding="utf-8",
    )

    # == Run pytest inside the generated project ================================
    env = os.environ.copy()
    src_dir = str(proot / "src")
    env["PYTHONPATH"] = src_dir + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )

    _run([sys.executable, "-m", "pytest", "-q"], cwd=proot, env=env)


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
        "apprc>=0.19.0,<0.20",
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
    assert "config/.env.shared" in package_data

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
    assert "PUBLISH_PYPI=true" in justfile_text
    assert "uv publish --token" not in justfile_text
    assert "RELEASE ${tag} PREPARED LOCALLY" in justfile_text
    assert "--all-extras --all-groups" in justfile_text

    readme_text = (proot / "README.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    assert 'python -m pip install -e ".[rag]"' in readme_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in readme_text
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
    assert "APP_RC.mount_cli" in cli_text
    assert "ensure_config_sections_registered()" in cli_text
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
        package_root / "config" / "__init__.py",
        package_root / "config" / "__init__.pyi",
        package_root / "config" / "_facade.py",
        package_root / "config" / "app.py",
        package_root / "config" / "bundle.py",
        package_root / "config" / "catalog.py",
        package_root / "config" / "sections" / "__init__.py",
        package_root / "config" / "sections" / "__init__.pyi",
        package_root / "config" / "sections" / "_facade.py",
        package_root / "config" / "sections" / "app.py",
    ]
    for config_file in config_files:
        assert config_file.is_file(), config_file

    assert not (package_root / "config" / "owners.py").exists()
    assert (package_root / "config" / ".env.shared").is_file()
    assert not (package_root / "paths.py").exists()
    assert not (package_root / "utils" / "path_resolver.py").exists()
    assert not (proot / ".env.template").exists()

    config_app_text = (package_root / "config" / "app.py").read_text(encoding="utf-8")
    config_facade_text = (package_root / "config" / "_facade.py").read_text(
        encoding="utf-8"
    )
    section_text = (package_root / "config" / "sections" / "app.py").read_text(
        encoding="utf-8"
    )
    bundle_text = (package_root / "config" / "bundle.py").read_text(encoding="utf-8")
    catalog_text = (package_root / "config" / "catalog.py").read_text(encoding="utf-8")
    shared_env_text = (package_root / "config" / ".env.shared").read_text(
        encoding="utf-8"
    )
    agents_text = (proot / "AGENTS.md").read_text(encoding="utf-8")

    assert "APP_RC = rc.AppRC.storage_only(" in config_app_text
    assert 'storage_env_key="BUBE_TEST_TMP_STORAGE"' in config_app_text
    assert 'command_name="bube_test_tmp"' in config_app_text
    assert 'index_filename="bube_test_tmp.apprc.toml"' in config_app_text
    assert 'storage_env_filename=".env.apprc-storage"' in config_app_text
    assert "@APP_RC.config(" in section_text
    assert "class AppSettings(rc.Config):" in section_text
    assert 'rc_path=("app",)' in section_text
    assert "rc.field(" in section_text
    assert "class BubeTestTmpConfig:" in bundle_text
    assert "app: AppSettings" in bundle_text
    assert "CONFIG_SECTIONS = CONFIG_SPEC.owners" in catalog_text
    assert "ensure_config_sections_registered" in catalog_text
    assert '"BubeTestTmpConfig"' in config_facade_text
    assert "APP_CONFIG" not in config_app_text
    assert "AppConfigKit" not in config_app_text
    assert "EnvConfig" not in section_text
    assert "env_field" not in section_text
    assert "env_owner" not in section_text
    assert "config_owner_for" not in section_text
    assert "AppRuntimeConfig" not in section_text
    assert "ConfigField" not in section_text
    assert "config_field" not in section_text
    assert "apprc.config" not in section_text
    assert 'prefix="BUBE_TEST_TMP_"' in section_text
    assert 'BUBE_TEST_TMP_MESSAGE="Hello from bube_test_tmp"' in shared_env_text
    assert "bube_test_tmp.config" in agents_text
    assert "apprc.cli" in agents_text
    assert "apprc.runtime_config" not in agents_text
    assert "apprc.logging" not in agents_text


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
    assert "PUBLISH_PYPI" in release_text
    assert "trusted-publishing" in release_text

    development_text = (bube_test_project / "docs" / "Development.md").read_text(
        encoding="utf-8"
    )
    assert "just release-check" in development_text
    assert "PUBLISH_PYPI=true" in development_text
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
    assert "RELEASE ${tag} PREPARED LOCALLY" in recipe
    assert "git push origin main ${tag}" in recipe


def test_scaffolded_project_includes_docs_scaffold(bube_test_project: Path) -> None:
    """Assert generated projects include the reusable docs scaffold."""
    proot = bube_test_project

    docs_files = [
        proot / "docs" / "README.md",
        proot / "docs" / "How-To-User-Guides.md",
        proot / "docs" / "Development.md",
        proot / "docs" / "References.md",
        proot / "docs" / "Explanations.md",
    ]
    svg_path = proot / "docs" / "assets" / "docs-reading-map.svg"

    for docs_file in docs_files:
        assert docs_file.is_file(), docs_file

    assert svg_path.is_file()
    ET.parse(svg_path)

    all_docs = "\n\n".join(path.read_text(encoding="utf-8") for path in docs_files)

    for placeholder in (
        "{my_project}",
        "<my_project>",
        "{github_username}",
        "<github_username>",
    ):
        assert placeholder not in all_docs
        assert placeholder not in svg_path.read_text(encoding="utf-8")

    for docs_file in docs_files:
        text = docs_file.read_text(encoding="utf-8")
        assert any(line.startswith("# 1. ") for line in text.splitlines())
        assert "> [!NOTE]" in text
        assert "> Related:" in text or "> Related links:" in text

    assert "Backlink:" not in all_docs
    assert "Backlinks:" not in all_docs

    readme_text = (proot / "README.md").read_text(encoding="utf-8")
    assert "docs/README.md" in readme_text

    references_text = (proot / "docs" / "References.md").read_text(encoding="utf-8")
    docs_readme_text = (proot / "docs" / "README.md").read_text(encoding="utf-8")
    development_text = (proot / "docs" / "Development.md").read_text(encoding="utf-8")
    how_to_text = (proot / "docs" / "How-To-User-Guides.md").read_text(encoding="utf-8")
    explanations_text = (proot / "docs" / "Explanations.md").read_text(encoding="utf-8")

    assert "bube_test_tmp --help" in references_text
    assert "bube_test_tmp version" in references_text
    assert "bube_test_tmp diagnose" in references_text
    assert "bube_test_tmp config setup --yes --storage-root" in references_text
    assert "CHANGELOG.md" in references_text
    assert "TODO.md" in references_text
    assert "python -m bube_test_tmp --help" in how_to_text
    assert "bube_test_tmp config doctor" in how_to_text

    assert "src/bube_test_tmp/config/.env.shared" in references_text
    assert "BUBE_TEST_TMP_APPRC_TOML" in references_text
    assert "BUBE_TEST_TMP_STORAGE" in references_text
    assert ".env.apprc-storage" in references_text
    assert "bube_test_tmp config storage add" in references_text
    assert "bube_test_tmp.config.sections" in references_text
    assert "bube_test_tmp.config.BubeTestTmpConfig" in references_text
    assert "bube_test_tmp.config.owners" not in references_text
    assert "AppRC" in explanations_text

    assert "Figure Visual Tokens" in references_text
    assert "References.md#figure-visual-tokens" in docs_readme_text
    assert "References.md#figure-visual-tokens" in development_text
    assert "README.md#2-documentation-standards" not in all_docs
    assert "Development.md#4-documentation-standards" in how_to_text


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
