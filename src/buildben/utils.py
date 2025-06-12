"""Utility functions for buildben"""

# %%
import os
import sys
import subprocess
import shutil
from pathlib import Path
from textwrap import dedent


# %%


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

PROJ_ROOT_SENTINELS = (".git", "pyproject.toml")


def find_project_root(start: Path | None = None) -> Path:
    """
    Walk upward from *start* (or cwd) until we find a sentinel that
    marks the project root. Raises RuntimeError if none found.
    """
    here = (start or Path.cwd()).resolve()  # <–– key change
    for candidate in [here, *here.parents]:
        if any((candidate / s).exists() for s in PROJ_ROOT_SENTINELS):
            return candidate
    raise RuntimeError(
        f"Not inside a buildben project; "
        f"looked for {PROJ_ROOT_SENTINELS} starting at {here}"
    )


if __name__ == "__main__":
    pass
    # %%
    print(find_project_root(Path(".")))
    print(find_project_root(Path("..")))
    print(find_project_root(None))

    # %%
    # !! Somewhere outside of a project, throws error
    find_project_root(Path("../../.."))


# %%
def detect_root() -> Path:
    """Reads environment Variable, or falls back to the project root"""
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    print(
        f"=> No PROJECT_ROOT env var — fallback to search for {PROJ_ROOT_SENTINELS}"
    )
    return find_project_root(Path.cwd())  # function from §1


if __name__ == "__main__":
    pass
    # %%
    detect_root()
    # %%


# %%
def copy_templates(transfers: dict[str, Path], tmpl_dir: Path) -> None:
    """Copy template files to the project root"""
    for tmpl_fn, dst_fp in transfers.items():
        tmpl_fp = tmpl_dir / tmpl_fn
        shutil.copy2(tmpl_fp, dst_fp, follow_symlinks=False)
    print(f"✓  Templates copied from {tmpl_dir}")


# %%
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
def warn_dir_overwrite(dir: Path) -> None:
    """Warn user if project root already exists"""
    _m = f"⚠️  {dir} exists and files may be overwritten. Continue? [y/N] "
    if dir.exists():
        answer = input(_m).lower()
        if answer not in {"y", "yes"}:
            sys.exit("Aborted by user")


# %%
def create__init__(dir: Path):
    """Create __init__.py files in a subdirectory"""
    (dir / "__init__.py").touch(exist_ok=True)
