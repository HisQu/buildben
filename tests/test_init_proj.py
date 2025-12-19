"""E2E test: scaffold a project, run its tests, then delete it."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
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
def bube_test_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a scaffolded project named 'bube_test_tmp' and clean it up afterwards."""
    # == Import your scaffolder =================================================
    # > This assumes your scaffolder code is in src/myproj/main.py
    from myproj import main as scaffolder

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
            "import os\n"
            "import subprocess\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "def test_main_module_executes() -> None:\n"
            "    project_root = Path(__file__).resolve().parents[1]\n"
            "    env = os.environ.copy()\n"
            "    src_dir = str(project_root / 'src')\n"
            "    env['PYTHONPATH'] = src_dir + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')\n"
            f"    subprocess.run([sys.executable, '-m', '{proj_name}.main', '--help'], cwd=str(project_root), env=env, check=True)\n"
        ),
        encoding="utf-8",
    )

    # == Run pytest inside the generated project ================================
    env = os.environ.copy()
    src_dir = str(proot / "src")
    env["PYTHONPATH"] = src_dir + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    _run([sys.executable, "-m", "pytest", "-q"], cwd=proot, env=env)


