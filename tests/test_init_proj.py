"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
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
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'init', str(project_root / 'storage'), '--name', 'default', '--default'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'doctor'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'list', '--json'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', 'config', 'show', '--json'], cwd=str(project_root), env=env, check=True)\n"
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
    assert project["dependencies"] == [
        "apprc @ git+https://github.com/HisQu/apprc.git",
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

    readme_text = (proot / "README.IGNORE.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    assert 'python -m pip install -e ".[rag]"' in readme_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in readme_text
    assert "bube_test_tmp version" in readme_text
    assert "bube_test_tmp diagnose" in readme_text
    assert "bube_test_tmp config init" in readme_text
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
    assert 'storage_root_env_key="BUBE_TEST_TMP_STORAGE"' in config_app_text
    assert 'env_prefix="BUBE_TEST_TMP_"' in owners_text
    assert 'BUBE_TEST_TMP_MESSAGE="Hello from bube_test_tmp"' in shared_env_text
    assert "bube_test_tmp.config" in agents_text
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

    readme_text = (proot / "README.IGNORE.md").read_text(encoding="utf-8")
    assert "docs/README.md" in readme_text

    references_text = (proot / "docs" / "References.md").read_text(encoding="utf-8")
    docs_readme_text = (proot / "docs" / "README.md").read_text(encoding="utf-8")
    development_text = (proot / "docs" / "Development.md").read_text(encoding="utf-8")
    how_to_text = (proot / "docs" / "How-To-User-Guides.md").read_text(encoding="utf-8")
    explanations_text = (proot / "docs" / "Explanations.md").read_text(encoding="utf-8")

    assert "bube_test_tmp --help" in references_text
    assert "bube_test_tmp version" in references_text
    assert "bube_test_tmp diagnose" in references_text
    assert "bube_test_tmp config init" in references_text
    assert "python -m bube_test_tmp --help" in how_to_text
    assert "bube_test_tmp config doctor" in how_to_text

    assert "src/bube_test_tmp/config/.env.shared" in references_text
    assert "BUBE_TEST_TMP_STORAGE" in references_text
    assert "bube_test_tmp.config.owners" in references_text
    assert "AppRC" in explanations_text

    assert "Figure Visual Tokens" in references_text
    assert "References.md#figure-visual-tokens" in docs_readme_text
    assert "References.md#figure-visual-tokens" in development_text
    assert "README.md#2-documentation-standards" not in all_docs
    assert "Development.md#4-documentation-standards" in how_to_text
