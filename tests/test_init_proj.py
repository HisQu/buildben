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
            "import json\n"
            "import os\n"
            "import subprocess\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "from typer.testing import CliRunner\n\n"
            f"from {proj_name}.cli.app import app\n\n"
            "def _project_env(project_root: Path) -> dict[str, str]:\n"
            "    env = os.environ.copy()\n"
            "    src_dir = str(project_root / 'src')\n"
            "    env['PYTHONPATH'] = src_dir + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')\n"
            "    return env\n\n"
            "def test_main_module_executes() -> None:\n"
            "    project_root = Path(__file__).resolve().parents[1]\n"
            "    env = _project_env(project_root)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}', '--help'], cwd=str(project_root), env=env, check=True)\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', '--help'], cwd=str(project_root), env=env, check=True)\n\n"
            "def test_typer_app_smoke() -> None:\n"
            "    runner = CliRunner()\n"
            '    for args in (["--help"], ["version"], ["diagnose"], ["diagnose", "--json"]):\n'
            "        result = runner.invoke(app, list(args))\n"
            "        assert result.exit_code == 0, result.output\n"
            '    payload = json.loads(runner.invoke(app, ["diagnose", "--json"]).output)\n'
            f"    assert payload['package'] == '{proj_name}'\n"
            "    assert payload['version'] == '0.1.0'\n"
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
    assert {"python-dotenv", "typer"} <= set(project["dependencies"])
    assert pyproject["project"]["scripts"]["bube_test_tmp"] == "bube_test_tmp.main:main"

    optional_dependencies = project.get("optional-dependencies", {})
    assert "dev" not in optional_dependencies
    assert "# [project.optional-dependencies]" in pyproject_text
    assert "# rag = [" in pyproject_text

    dependency_groups = pyproject["dependency-groups"]
    assert {"pytest>=8.2", "pyright>=1.1", "ruff>=0.4"} <= set(dependency_groups["dev"])

    envrc_text = (proot / ".envrc").read_text(encoding="utf-8")
    assert "--all-extras" in envrc_text
    assert "--all-groups" in envrc_text
    assert "--no-default-groups" in envrc_text
    assert "uv sync --frozen --all-extras --all-groups" in envrc_text

    justfile_text = (proot / "justfile").read_text(encoding="utf-8")
    assert "uv sync --all-extras --all-groups --locked" in justfile_text
    assert "uv sync --frozen --all-extras --all-groups" in justfile_text
    assert "uv sync --check --all-extras --all-groups" in justfile_text

    readme_text = (proot / "README.IGNORE.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e "."' in readme_text
    assert 'python -m pip install -e ".[rag]"' in readme_text
    assert 'python -m pip install -e "." --group dev' in readme_text
    assert 'python -m pip install -e ".[rag]" --group dev' in readme_text


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
    how_to_text = (proot / "docs" / "How-To-User-Guides.md").read_text(encoding="utf-8")
    assert "bube_test_tmp --help" in references_text
    assert "bube_test_tmp version" in references_text
    assert "bube_test_tmp diagnose" in references_text
    assert "python -m bube_test_tmp --help" in how_to_text
