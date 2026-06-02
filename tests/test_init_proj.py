"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
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


@pytest.fixture()
def bube_test_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Path, None, None]:
    """Create a scaffolded project named 'bube_test_tmp' and clean it up afterwards."""
    # == Import the real scaffolder =============================================
    import buildben.init_proj as scaffolder

    # -- Make the test non-interactive -----------------------------------------
    # > If warn_dir_overwrite ever prompts, CI will hang. Nobody wants that.
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
    # > (Exit code 5 = "no tests collected".) :contentReference[oaicite:1]{index=1}
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
            "def test_generated_sources_compile() -> None:\n"
            "    project_root = Path(__file__).resolve().parents[1]\n"
            f"    py_compile.compile(project_root / 'src' / '{proj_name}' / 'main.py', doraise=True)\n"
            f"    py_compile.compile(project_root / 'src' / '{proj_name}' / 'config' / 'app.py', doraise=True)\n"
            f"    py_compile.compile(project_root / 'src' / '{proj_name}' / 'config' / 'owners.py', doraise=True)\n\n"
            "def test_main_module_executes_when_apprc_is_installed() -> None:\n"
            "    if importlib.util.find_spec('apprc') is None:\n"
            "        pytest.skip('Generated project runtime smoke test needs apprc installed.')\n"
            "    project_root = Path(__file__).resolve().parents[1]\n"
            "    env = os.environ.copy()\n"
            "    src_dir = str(project_root / 'src')\n"
            "    env['PYTHONPATH'] = src_dir + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')\n"
            "    env['XDG_CONFIG_HOME'] = str(project_root / '.test-config')\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', '--help'], cwd=str(project_root), env=env, check=True)\n"
            f"    before = subprocess.run([sys.executable, '-m', '{proj_name}.main', 'config', 'doctor'], cwd=str(project_root), env=env, text=True, capture_output=True, check=False)\n"
            "    assert before.returncode == 1\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', 'config', 'init', str(project_root / 'storage'), '--name', 'default', '--default'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', 'config', 'doctor'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', 'config', 'show', '--json'], cwd=str(project_root), env=env, check=True)\n"
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


def test_scaffolded_project_uses_dependency_group_template(
    bube_test_project: Path,
) -> None:
    """Assert generated dependency docs and commands match the template policy."""
    proot = bube_test_project

    pyproject_path = proot / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)

    project = pyproject["project"]
    assert project["dependencies"] == ["apprc @ git+https://github.com/HisQu/apprc.git"]
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
    assert "uv lock" in justfile_text

    readme_text = (proot / "README.IGNORE.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    assert 'python -m pip install -e ".[rag]"' in readme_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in readme_text
    assert "bube_test_tmp config init" in readme_text
    assert "bube_test_tmp config doctor" in readme_text


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

    main_text = (package_root / "main.py").read_text(encoding="utf-8")
    config_app_text = (package_root / "config" / "app.py").read_text(encoding="utf-8")
    owners_text = (package_root / "config" / "owners.py").read_text(encoding="utf-8")
    shared_env_text = (package_root / "config" / ".env.shared").read_text(
        encoding="utf-8"
    )
    agents_text = (proot / "AGENTS.md").read_text(encoding="utf-8")

    assert "bootstrap_cli_env" in main_text
    assert "setup_logging" in main_text
    assert "APP_CONFIG.typer_app" in main_text
    assert "AppConfigKit" in config_app_text
    assert 'storage_root_env_key="BUBE_TEST_TMP_STORAGE"' in config_app_text
    assert 'env_prefix="BUBE_TEST_TMP_"' in owners_text
    assert 'BUBE_TEST_TMP_MESSAGE="Hello from bube_test_tmp"' in shared_env_text
    assert "bube_test_tmp.config" in agents_text
    assert "apprc.logging" in agents_text
