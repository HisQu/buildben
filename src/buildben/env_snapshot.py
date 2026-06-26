#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from . import utils

CMD_NAME = "env-snapshot"
CMD_ALIASES = ["snp"]
DOC = (
    "Snapshot a Python project into an experiment requirements.lock, "
    "experiment.env, wheel, and sdist. "
    f"Aliases: {CMD_ALIASES}"
)


def _add_my_parser(subparsers: argparse._SubParsersAction) -> None:
    """Attach the env-snapshot sub-parser to the CLI aggregator.

    :param subparsers: Parent argparse subparser registry.
    :return: None.
    """
    p: argparse.ArgumentParser = subparsers.add_parser(
        name=CMD_NAME,
        aliases=CMD_ALIASES,
        help=DOC,
        description=DOC,
    )
    p.add_argument(
        "experiment_dir",
        help="Experiment directory to write lock and environment files into.",
    )
    p.set_defaults(func=_run)


def _project_name(project_root: Path) -> str:
    """Return the display name for the current project.

    :param project_root: Discovered project root.
    :return: Environment-provided project name or directory fallback.
    """
    return os.getenv("PROJECT_NAME") or project_root.name


def _resolve_experiment_dir(project_root: Path, raw_path: str) -> Path:
    """Resolve an experiment directory and require it to stay inside the repo.

    :param project_root: Discovered project root.
    :param raw_path: CLI argument supplied as ``experiment_dir``.
    :return: Absolute experiment directory path.
    :raises SystemExit: If the path resolves outside the project root.
    """
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    experiment_dir = candidate.resolve()
    try:
        experiment_dir.relative_to(project_root)
    except ValueError as exc:
        raise SystemExit(
            "env-snapshot: experiment_dir must resolve inside the project root."
        ) from exc
    return experiment_dir


def _run_checked(command: list[str], *, cwd: Path, failure_hint: str) -> str:
    """Run a required command and convert failures into CLI-friendly exits.

    :param command: Executable and arguments to run.
    :param cwd: Working directory for the command.
    :param failure_hint: Message shown if the command fails.
    :return: Captured stdout.
    :raises SystemExit: If the command exits non-zero.
    """
    try:
        return utils.run_command(command, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f"\n{stderr}" if stderr else ""
        raise SystemExit(f"{failure_hint}{detail}") from exc


def _current_commit(project_root: Path) -> tuple[str, str]:
    """Return the current short commit hash and ISO commit date.

    :param project_root: Git-backed project root.
    :return: Short commit hash and commit date text.
    """
    commit_hash = _run_checked(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=project_root,
        failure_hint="env-snapshot requires a git repository with at least one commit.",
    )
    commit_date = _run_checked(
        ["git", "show", "-s", "--format=%cd", "--date=iso", commit_hash],
        cwd=project_root,
        failure_hint="env-snapshot could not inspect the current git commit.",
    )
    return commit_hash, commit_date


def _tag_commit(project_root: Path, project_name: str, commit_hash: str) -> None:
    """Create an annotated snapshot tag if it does not already exist.

    :param project_root: Git-backed project root.
    :param project_name: Display name for the project.
    :param commit_hash: Short git commit hash being snapshotted.
    :return: None.
    """
    tag = f"env-snapshot-{commit_hash}"
    message = f"Snapshot of {project_name} at {commit_hash}"
    subprocess.run(
        ["git", "tag", "-a", tag, "-m", message],
        cwd=project_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _write_experiment_env(
    env_path: Path,
    *,
    commit_hash: str,
    lock_path: Path,
    project_root: Path,
) -> None:
    """Write reproducibility metadata for the experiment snapshot.

    :param env_path: Destination ``experiment.env`` path.
    :param commit_hash: Short git commit hash being snapshotted.
    :param lock_path: Requirements lock file path.
    :param project_root: Project root used to compute relative paths.
    :return: None.
    """
    lock_relative = lock_path.relative_to(project_root)
    env_path.write_text(
        f"COMMIT_HASH={commit_hash}\nLOCK_FILE={lock_relative}\n",
        encoding="utf-8",
    )


def _ensure_uv_lock(project_root: Path) -> None:
    """Require a uv lock file before exporting frozen requirements.

    :param project_root: Project root expected to contain ``uv.lock``.
    :return: None.
    :raises SystemExit: If ``uv.lock`` is missing.
    """
    if not (project_root / "uv.lock").is_file():
        raise SystemExit(
            "env-snapshot requires uv.lock. Run `uv lock` in the project root first."
        )


def _run(args: argparse.Namespace) -> None:
    """Create a reproducibility snapshot for one experiment directory.

    :param args: Parsed CLI arguments.
    :return: None.
    """
    project_root = utils.find_project_root()
    project_name = _project_name(project_root)
    experiment_dir = _resolve_experiment_dir(project_root, args.experiment_dir)
    setup_dir = experiment_dir / "_setup"
    lock_path = setup_dir / "requirements.lock"
    env_path = experiment_dir / "experiment.env"

    experiment_dir.mkdir(parents=True, exist_ok=True)
    setup_dir.mkdir(parents=True, exist_ok=True)
    _ensure_uv_lock(project_root)

    experiment_relative = experiment_dir.relative_to(project_root)
    print(f"📂  Project '{project_name}' in '{project_root}'")
    print(f"🔍  Targeting experiment directory: '{experiment_relative}'")

    commit_hash, commit_date = _current_commit(project_root)
    print(f"🔖  Using commit: {commit_hash} ({commit_date})")
    _tag_commit(project_root, project_name, commit_hash)

    print(f"📦  Building source distribution and wheel into {setup_dir}")
    _run_checked(
        ["uv", "build", "--out-dir", str(setup_dir), "--no-sources"],
        cwd=project_root,
        failure_hint="env-snapshot could not build release artifacts with uv.",
    )

    print(f"📌  Exporting locked requirements to {lock_path}")
    _run_checked(
        [
            "uv",
            "export",
            "--format",
            "requirements.txt",
            "--all-extras",
            "--all-groups",
            "--no-emit-project",
            "--output-file",
            str(lock_path),
            "--locked",
        ],
        cwd=project_root,
        failure_hint=(
            "env-snapshot could not export requirements from uv.lock. "
            "Run `uv lock` if pyproject.toml changed."
        ),
    )

    print(f"🔖  Writing {env_path.name}")
    _write_experiment_env(
        env_path,
        commit_hash=commit_hash,
        lock_path=lock_path,
        project_root=project_root,
    )

    print("Next steps:")
    print(f"  uv pip install -r {lock_path.relative_to(project_root)}")


if __name__ == "__main__":
    _parser = argparse.ArgumentParser()
    _add_my_parser(_parser.add_subparsers(dest="cmd", required=True))
    parsed_args = _parser.parse_args()
    parsed_args.func(parsed_args)
