"""Utility functions for buildben"""

# %%
import os
import sys
import subprocess
import shutil
from pathlib import Path
from textwrap import dedent
import ast
from collections.abc import Iterable

from typing import Iterable, Sequence


# %%
# =====================================================================
# === Shell
# =====================================================================


def run_command(command: str | list[str], cwd=None, quiet=True) -> str:
    """Run a shell command and check for errors."""

    shell = True if isinstance(command, str) else False

    if isinstance(command, list):
        shell = False
    elif isinstance(command, str):
        shell = True
        command = dedent(command).strip()

    result = subprocess.run(
        command,
        shell=shell,  # < If command is not a list but a string
        cwd=cwd,  # < Current working directory
        # capture_output=True,  # < Capture output and error streams
        stdout=subprocess.PIPE,  # < Capture output stream
        stderr=subprocess.PIPE,  # < Capture error stream
        text=True,  # < Output as text (not bytes)
    )

    if result.returncode != 0:
        print(f"\n!!\n!! Error executing command: \n{command} \n")
        print(result.stderr, "!!\n!!\n")
        raise subprocess.CalledProcessError(result.returncode, command)

    if not quiet:
        print(result.stdout, end="")

    return result.stdout.strip()


if __name__ == "__main__":
    print(run_command("ls"))
    print(
        run_command(
            """ls \
                -l \
                -a \
            """
        )
    )
    print(run_command(["ls", "-l", "-a"]))


# %%
# =====================================================================
# === Git
# =====================================================================
def git_init(PROOT: Path) -> None:
    """Initialize a git repository in the given project root directory."""

    ### Rename "master" branch to "main"
    run_command("git config --global init.defaultBranch main", cwd=PROOT)

    ### Initialize git repo and commit
    subprocess.run(["git", "init"], cwd=PROOT, check=True)
    subprocess.run(["git", "add", "."], cwd=PROOT, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial scaffold from buildben"],
        cwd=PROOT,
        check=True,
    )

    subprocess.run(["git", "branch", "-m", "main"], cwd=PROOT, check=True)


# %%
# =====================================================================
# === Path Resolution
# =====================================================================


def find_project_root(
    start: Path | None = None,
    sentinels: Sequence[str] = (".git", "pyproject.toml", "setup.py"),
) -> Path:
    """
    Returns environment variable "PROJECT_ROOT". Otherwise, falls back
    to Walk upward from *start* (or cwd) until we find a sentinel that
    marks the project root. Raises RuntimeError if none found.
    """
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()  # !! Early exit

    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if any((candidate / s).exists() for s in sentinels):
            return candidate  # < Found!
    raise RuntimeError(
        f"Not inside a project; " f"looked for {sentinels} starting at {here}"
    )


if __name__ == "__main__":
    print(find_project_root(Path(".")))
    print(find_project_root(None))

    # %%
    # !! Somewhere outside of a project, throws error
    # print(find_project_root(Path("..")))
    # find_project_root(Path("../../.."))


# %%
# =====================================================================
# === Create Files
# =====================================================================


def copy_templates(transfers: dict[str, Path], tmpl_dir: Path) -> None:
    """Copy template files to the project root"""
    for tmpl_fn, dst_fp in transfers.items():
        tmpl_fp = tmpl_dir / tmpl_fn
        shutil.copy2(tmpl_fp, dst_fp, follow_symlinks=False)
    print(f"✓  Templates copied from {tmpl_dir}")


# %%
def warn_dir_overwrite(dir: Path) -> None:
    """Warn user if project root already exists"""
    _m = f"⚠️  {dir} exists and files may be overwritten. Continue? [y/N] "
    if dir.exists():
        answer = input(_m).lower()
        if answer not in {"y", "yes"}:
            sys.exit("Aborted by user")


# %%
# =====================================================================
# === Create __init__.py
# =====================================================================

def _module_source_path(pkg_dir: Path, module_name: str) -> Path:
    """Resolve a module name to a source path inside *pkg_dir*.

    Supports:
    - <pkg_dir>/<module_name>.py
    - <pkg_dir>/<module_name>/__init__.py
    """
    file_path = pkg_dir / f"{module_name}.py"
    if file_path.is_file():
        return file_path

    pkg_init = pkg_dir / module_name / "__init__.py"
    if pkg_init.is_file():
        return pkg_init

    raise FileNotFoundError(
        f"Cannot find module '{module_name}' as '{file_path}' or '{pkg_init}'."
    )


def _top_level_function_names(py_path: Path, include_private: bool) -> list[str]:
    """Extract top-level function names (def/async def) from a Python source file."""
    src = py_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(py_path))

    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not include_private and node.name.startswith("_"):
                continue
            names.append(node.name)

    names.sort()
    return names


def _format_from_import_block(module_name: str, names: list[str]) -> str:
    """Format a re-export block: from .mod import (a, b, c)."""
    if not names:
        return ""

    lines: list[str] = [f"from .{module_name} import (\n"]
    for name in names:
        lines.append(f"    {name},\n")
    lines.append(")\n")
    return "".join(lines)


def create_init_dot_py(
    pkg_dir: Path,
    imports: Iterable[str] | None = None,
    *,
    flatten_functions: bool = False,
    include_private: bool = False,
) -> None:
    """Create ``__init__.py`` inside *pkg_dir*.

    If *imports* is provided, write::

        from . import <comma-separated names>

    If *flatten_functions* is True, also re-export top-level functions from each
    listed module, so users can do::

        import my_project.utils as u
        u.some_function(...)

    :param pkg_dir: Directory that should behave as a Python package.
    :param imports: Module names to import eagerly, relative to *pkg_dir*.
    :param flatten_functions: If True, re-export top-level functions from each module.
    :param include_private: If True, include names starting with ``_``.
    :raises FileNotFoundError: If a requested module file cannot be found.
    :raises ValueError: If flattened function names collide across modules.
    """
    init_path = pkg_dir / "__init__.py"
    modules = list(imports) if imports else []

    if not modules:
        init_path.touch(exist_ok=True)
        return

    parts: list[str] = [f"from . import {', '.join(modules)}\n"]

    if flatten_functions:
        seen: dict[str, str] = {}

        for module_name in modules:
            source_path = _module_source_path(pkg_dir, module_name)
            func_names = _top_level_function_names(
                source_path, include_private=include_private
            )

            for fn in func_names:
                prev = seen.get(fn)
                if prev is not None and prev != module_name:
                    raise ValueError(
                        f"Flattened name conflict: '{fn}' in both '{prev}' and '{module_name}'."
                    )
                seen[fn] = module_name

            block = _format_from_import_block(module_name, func_names)
            if block:
                parts.append("\n")
                parts.append(block)

    init_path.write_text("".join(parts), encoding="utf-8")


# %%
# =====================================================================
# === Edit Files
# =====================================================================


def substitute_placeholders(
    filepaths: list[Path], placeholders: dict[str, str]
) -> None:
    """Substitute placeholders in a string"""
    for fp in filepaths:
        fp: Path
        text = fp.read_text(encoding="utf-8")
        for old, new in placeholders.items():
            text = text.replace(old, new)
        fp.write_text(text, encoding="utf-8")
        # > Pathlib closes the file automatically
    print(f"✓  Placeholders substituted: {list(placeholders.keys())}")




# %%
# ====================================================================
# === Docker
# ====================================================================


class DockerNotInstalledError(RuntimeError):
    """Raised when the `docker` command is not found on PATH."""


class DockerDaemonNotRunningError(RuntimeError):
    """Raised when Docker is installed but the daemon/service is unreachable."""


def assert_docker_available(timeout: float = 3.0) -> None:
    """
    Ensure that Docker is installed *and* the engine is responding.

    Parameters
    ----------
    timeout : float, optional
        Seconds to wait for `docker info` before giving up.  Default is 3 s.

    Raises
    ------
    DockerNotInstalledError
        If the `docker` executable cannot be located.
    DockerDaemonNotRunningError
        If the CLI exists but cannot talk to the Docker engine.
    """
    # 1. Is the CLI on PATH?
    if (
        shutil.which("docker") is None
    ):  # std-lib check :contentReference[oaicite:3]{index=3}
        raise DockerNotInstalledError(
            "Docker is not installed or the 'docker' command is not on your PATH. "
            "Install Docker Desktop (Windows/macOS) or Docker Engine (Linux) "
            "and then re-run this program."
        )

    # 2. Does the daemon answer?
    try:
        completed = subprocess.run(
            [
                "docker",
                "info",
                "--format",
                "{{json .ServerVersion}}",
            ],  # < avoids stdout noise
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,  # < we inspect returncode ourselves
        )
    except subprocess.TimeoutExpired as exc:
        raise DockerDaemonNotRunningError(
            f"Docker CLI responded but the engine did not answer within {timeout}s. "
            "Ensure the Docker service is running."
        ) from exc

    if completed.returncode != 0:
        #  > The CLI’s exit status is 1 when it cannot reach the daemon
        raise DockerDaemonNotRunningError(
            "Docker is installed, but the engine is not running or you lack permission "
            "to access the socket. Start Docker Desktop or, on Linux, run "
            "`sudo systemctl start docker` and make sure your user is in the "
            "'docker' group."
        )


if __name__ == "__main__":
    try:
        assert_docker_available()
        print("✓ Docker is installed and the daemon is running.")
    except (DockerNotInstalledError, DockerDaemonNotRunningError) as err:
        print(f"✗ {err}")

# %%
