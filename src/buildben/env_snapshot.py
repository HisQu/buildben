#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
import sys
from textwrap import dedent
import subprocess

from . import utils

CMD_NAME = "env-snapshot"  # < Name of the CLI-command
CMD_ALIASES = ["snp"]  # < Alias shortcut of the CLI-command
DOC = f"Snapshot a Python project into requirements.lock, experiment.env, and Dockerfile. Aliases: {CMD_ALIASES}"


def _add_my_parser(subparsers: argparse._SubParsersAction) -> None:
    p: argparse.ArgumentParser = subparsers.add_parser(
        name=CMD_NAME,
        aliases=CMD_ALIASES,
        help=DOC,
        description=DOC,
    )
    # p.add_argument(
    #     "-e",
    #     "--exp-dir",
    #     dest="experiment_dir",
    #     help="Experiment directory to write lock & env files",
    # )

    p.add_argument(
        "experiment_dir",
        nargs="?",  # < zero-or-one positional value
        # help=argparse.SUPPRESS,  # < Hide duplicate from help text
        help="Experiment directory to write lock & env files",
    )

    p.add_argument(
        "-d",
        "--dockerize",
        action="store_true",
        default=False,
        help="Write Dockerfile, .dockerignore and build Docker image",
    )

    p.add_argument(
        "--py-base",
        "-b",
        default="python:3.12-slim",
        help="Base for docker-image (default 'python:3.12-slim')",
    )

    # > Entrypoint, retrieved as args.func in cli.py
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> None:

    # === Retrieve Variables ==========================================
    PR_ROOT: Path = utils.find_project_root()
    PR_NAME = os.getenv("PROJECT_NAME")

    dockerize = args.dockerize

    ### Absolute Path
    EXP_DIR: Path = Path(args.experiment_dir).resolve()
    EXP_DIR_REL: Path = EXP_DIR.relative_to(PR_ROOT)
    SETUP_DIR: Path = EXP_DIR / "_setup"
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    SETUP_DIR.mkdir(parents=True, exist_ok=True)
    
    ### Outputs
    LOCK_FP: Path = SETUP_DIR / "requirements.lock"
    LOCK_REL: Path = LOCK_FP.relative_to(PR_ROOT)
    ENV_FP: Path = EXP_DIR / "experiment.env"
    DOCKERIGNORE_FP: Path = SETUP_DIR / "Dockerfile.dockerignore"
    DOCKERFILE_FP: Path = SETUP_DIR / "Dockerfile"

    ### Change Directory
    # os.chdir(PR_ROOT)

    ### Print info
    print(f"📂  Project '{PR_NAME}' in '{PR_ROOT}'")
    print(f"🔍  Targetting experiment directory: '{EXP_DIR_REL}'")

    # === Capture Commit Hash =========================================

    commit_hash: str = utils.run_command("git rev-parse --short HEAD")
    timepoint: str = utils.run_command(
        f"git show -s --format=%cd --date=iso {commit_hash}", cwd=PR_ROOT
    )
    print(f"🔖  Using Commit: {commit_hash} ({timepoint})")

    # === Write experiment.env ========================================
    print(f"🔖  Writing {ENV_FP.name} (for DVC, MLflow, etc.) ...")
    ENV_FP.write_text(f"COMMIT_HASH={commit_hash}\nLOCK_FILE={LOCK_FP.name}\n")

    # === Git tag current commit ======================================
    tag_msg = f"Snapshot of {PR_NAME} at {commit_hash}"
    print(f"🔖  Tagging commit {commit_hash} in git: '{tag_msg}'")
    cmd = [
        "git",
        "tag",
        "-a",
        f"env-snapshot-{commit_hash}",
        "-m",
        tag_msg,
    ]
    subprocess.run(
        cmd, cwd=PR_ROOT, check=False
    )  # Don't fail if already exists

    # =================================================================
    # === Make a wheel and sdist
    # =================================================================
    print(f"📦  Building source distribution and wheel ...")
    cmd = [
        "python",
        "-m",
        "build",
        "--sdist",
        "--wheel",
        "--outdir",
        str(SETUP_DIR),
    ]
    subprocess.run(cmd, cwd=PR_ROOT, check=True)

    # =================================================================
    # === Freeze the live venv
    # =================================================================
    print(f"📌 ... pip-compiling environment ...")
    # utils.run_command(
    cmd = [
        "pip-compile",
        # "--generate-hashes", # !! Doesn't work with pip 25 and pip-compile 7.4.1
        "--allow-unsafe",
        "--extra",
        "dev",
        "--output-file",
        str(LOCK_FP),
        str(PR_ROOT / "pyproject.toml"),
    ]
    # print("\n".join(cmd))  # < Print command for debugging
    subprocess.run(cmd) # !! Uncomment

    print(f"📌  Environment frozen to {LOCK_REL}")

    # =================================================================
    # === Write .dockerignore
    # =================================================================
    print(dockerize)
    if dockerize:
        raise NotImplementedError(
            "Dockerization is not yet implemented in env_snapshot.py"
        )
    # !! Main issue = need to set up git+ssh to access private repos

    # > Prevent copying EVERY experiment into the Docker image!
    dockerignore = dedent(
        f""" \
        # > Ignore everything under experiments, but keep the target directory!
        experiments/** 
        !{EXP_DIR_REL}/**
        
        .direnv/
        .venv/
        venv/
        env/
        
        .git/
        .gitignore
        
        __pycache__/
        *.py[cod]
        *$py.class
        *.egg-info/
        .eggs/
        
        tests/
        .pytest_cache/
        .coverage
        htmlcov/
        
        .vscode/
        .idea/
        .DS_Store
        Thumbs.db
        
        *.log
        logs/
        *.sqlite3
        
        .env
        .env.*
        .secrets.env
        """
    )
    if dockerize:
        DOCKERIGNORE_FP.write_text(dockerignore)

    # =================================================================
    # === Write Dockerfile
    # =================================================================

    image_tag = f"{PR_NAME}:{commit_hash}"
    dockerfile = dedent(
        f""" \
        # syntax=docker/dockerfile:1
        ### Builds Image {image_tag}
        
        # === 1️⃣ Builder: has git =====================================
        FROM {args.py_base} AS builder
        WORKDIR /app # < Root of the Repo inside the container
        
        ### Install git 
        RUN apt-get update \\
            && apt-get install -y --no-install-recommends git \\
            && rm -rf /var/lib/apt/lists/*
        
        ### Install dependencies
        COPY {LOCK_REL} requirements.lock
        RUN pip install \\
            # --require-hashes \\
            --no-cache-dir \\
            -r requirements.lock

        ### Force-checkout the exact commit & Install
        # > Copy the complete repo to WORKDIR
        COPY . .
        RUN git -C . checkout {commit_hash} && pip install -e .
        
        # === 2️⃣ runtime: tiny, no git ================================
        FROM python:3.12-slim
        WORKDIR /app
        
        # > Bring in installed package
        COPY --from=builder /usr/local /usr/local  
        # > (optional) Copy source for debugging to WORKDIR
        COPY . .
        
        # > Make env vars available TODO: this creates a .direnv. !!! Find a better solution
        # CMD ["source", ".envrc"]
        
        # > Executables
        # CMD ["python", "-m", "your_pkg.cli"]
        """
    )
    if dockerize:
        DOCKERFILE_FP.write_text(dockerfile)
        print(f"🐳  Wrote Dockerfile & .dockerignore")

    # =================================================================
    # === Build Docker Image
    # =================================================================
    if dockerize:
        print(f"🐳 ...  Building Docker image {image_tag} ...")
        utils.assert_docker_available()  # < Check docker
        utils.run_command(
            f"""docker build \\
            --tag {image_tag} \\
            --file {DOCKERFILE_FP} \\
            {PR_ROOT}
            """
        )

        size = utils.run_command(
            f"docker image ls | grep {commit_hash}"
        ).split()[-1]

        print(f"🐳  Done building [Imagesize = {size}]")

    # =================================================================
    # === Next steps
    # =================================================================
    print("Next steps:")
    if dockerize:
        print(f"🚀  Run interactively:\tdocker run -it {image_tag}")
        print(f"👉  Push to ??:\tdocker push {image_tag}")
        print(
            f"🚮  Remove image:\tdocker image rm {image_tag}   (layers stay deduped)"
        )

    # %%
