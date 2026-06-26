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

    # == Add a minimal smoke test into the generated project ====================
    # > Pytest exits with code 5 when it collects no tests, so we create one.
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
            "        'config/app.py',\n"
            "        'config/owners.py',\n"
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
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'set', 'app.message', 'Hello local storage'], cwd=str(project_root), env=env, check=True)\n"
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
        "apprc>=0.15.1,<0.16",
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
    assert "_check-pypi-api-key" in justfile_text
    assert "uv build --no-sources" in justfile_text
    assert "twine check dist/*" in justfile_text
    assert 'uv publish --token "$PYPI_API_KEY"' in justfile_text
    assert "uv version --bump" in justfile_text
    assert 'verify-pypi requirement="bube_test_tmp"' in justfile_text

    readme_text = (proot / "README.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    assert 'python -m pip install -e ".[rag]"' in readme_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in readme_text
    assert "bube_test_tmp version" in readme_text
    assert "bube_test_tmp diagnose" in readme_text
    assert "bube_test_tmp config setup --yes --storage-root" in readme_text
    assert "bube_test_tmp config doctor" in readme_text


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
    assert "APP_CONFIG.typer_app" in cli_text
    assert "bootstrap_cli_env" in cli_text
    assert "config_request_skips_runtime_bootstrap" in cli_text
    assert "--env-file-overrides-os-environ" in cli_text
    assert "--skip-dotenv-layers" in cli_text
    assert "setup_logging" in cli_text
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

    assert (package_root / "config" / "__init__.py").is_file()
    assert (package_root / "config" / "app.py").is_file()
    assert (package_root / "config" / "owners.py").is_file()
    assert (package_root / "config" / ".env.shared").is_file()
    assert not (package_root / "paths.py").exists()
    assert not (package_root / "utils" / "path_resolver.py").exists()
    assert not (proot / ".env.template").exists()

    config_app_text = (package_root / "config" / "app.py").read_text(encoding="utf-8")
    owners_text = (package_root / "config" / "owners.py").read_text(encoding="utf-8")
    shared_env_text = (package_root / "config" / ".env.shared").read_text(
        encoding="utf-8"
    )
    agents_text = (proot / "AGENTS.md").read_text(encoding="utf-8")

    assert "AppConfigKit" in config_app_text
    assert "APP_CONFIG_ENVS" in config_app_text
    assert "envs=APP_CONFIG_ENVS" in config_app_text
    assert 'storage_env_key="BUBE_TEST_TMP_STORAGE"' in config_app_text
    assert 'command_name="bube_test_tmp"' in config_app_text
    assert 'apprc_toml_filename="bube_test_tmp.apprc.toml"' in config_app_text
    assert "EnvConfig" in owners_text
    assert "env_field" in owners_text
    assert "env_owner" in owners_text
    assert "config_owner_for" in owners_text
    assert "AppRuntimeConfig" in owners_text
    assert "ConfigField" not in owners_text
    assert "config_field" not in owners_text
    assert "apprc.config" not in owners_text
    assert 'env_prefix="BUBE_TEST_TMP_"' in owners_text
    assert 'BUBE_TEST_TMP_MESSAGE="Hello from bube_test_tmp"' in shared_env_text
    assert "bube_test_tmp.config" in agents_text
    assert "apprc.runtime_config" in agents_text
    assert "apprc.logging" in agents_text


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
    assert "python -m bube_test_tmp --help" in how_to_text
    assert "bube_test_tmp config doctor" in how_to_text

    assert "src/bube_test_tmp/config/.env.shared" in references_text
    assert "BUBE_TEST_TMP_APPRC_TOML" in references_text
    assert "BUBE_TEST_TMP_STORAGE" in references_text
    assert "bube_test_tmp.config.owners" in references_text
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
    assert "buildben/_templates_proj/_src-cli-app.py.tmpl" in names


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
