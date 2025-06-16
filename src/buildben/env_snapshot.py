#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from textwrap import dedent


from . import utils

CMD_NAME = "env-snapshot"  # < Name of the CLI-command
CMD_ALIASES = ["snp"]  # < Alias shortcut of the CLI-command
DOC = "Snapshot a Python project into requirements.lock, experiment.env, and Dockerfile"


def _add_my_parser(subparsers: argparse._SubParsersAction) -> None:
    p: argparse.ArgumentParser = subparsers.add_parser(
        name=CMD_NAME,
        aliases=CMD_ALIASES,
        help=DOC,
        description=DOC,
    )
    p.add_argument(
        "--target-dir",
        "-t",
        required=True,
        help="Directory to write lock & env files",
    )
    p.add_argument(
        "--py-base",
        "-b",
        default="python:3.12-slim",
        help="Base image (default 'python:3.12-slim')",
    )
    # > Entrypoint, retrieved as args.func in cli.py
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> None:

    # === Retrieve Variables ==========================================
    PR_ROOT: Path = utils.detect_root()
    PR_NAME = os.getenv("PROJECT_NAME")

    ### Absolute Path
    TARGET_DIR: Path = PR_ROOT / args.target_dir
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_REL: Path = TARGET_DIR.relative_to(PR_ROOT)

    ### Outputs
    LOCK_FP: Path = TARGET_DIR / "requirements.lock"
    LOCK_REL: Path = LOCK_FP.relative_to(PR_ROOT)
    ENV_FP: Path = TARGET_DIR / "experiment.env"
    DOCKERIGNORE_FP: Path = TARGET_DIR / "Dockerfile.dockerignore"
    DOCKERFILE_FP: Path = TARGET_DIR / "Dockerfile"

    ### Change Directory
    os.chdir(PR_ROOT)

    # === Capture Commit Hash =========================================

    commit_hash: str = utils.run_command("git rev-parse --short HEAD")
    timepoint: str = utils.run_command(
        f"git show -s --format=%cd --date=iso {commit_hash}", cwd=PR_ROOT
    )
    print(f"🔖  Using Commit: {commit_hash} ({timepoint})")

    # =================================================================
    # === Freeze the live venv
    # =================================================================

    print(f"📌 ... pip-compiling environment ...")
    utils.run_command(
        f"""pip-compile \\
            --generate-hashes \\
            --allow-unsafe \\
            --extra dev \\
            --output-file {LOCK_FP} \\
            pyproject.toml
        """,
    )
    print(f"📌  Environment frozen to {LOCK_REL}")

    # === Write experiment.env ========================================
    ENV_FP.write_text(f"COMMIT_HASH={commit_hash}\nLOCK_FILE={LOCK_FP.name}\n")
    print(f"🔖  Wrote {ENV_FP.name} (for DVC, MLflow, etc.)")

    # =================================================================
    # === Write .dockerignore
    # =================================================================
    # > Prevent copying EVERY experiment into the Docker image!
    dockerignore = dedent(
        f""" \
        # > Ignore everything under experiments ...
        experiments/**
        # > ... but keep the target directory!
        !{TARGET_REL}/**
        """
    )
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
            --require-hashes \\
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
        
        # > Make experminet-related env vars available
        CMD ["source", ".envrc"]
        
        # > Executables
        # CMD ["python", "-m", "your_pkg.cli"]
        """
    )
    DOCKERFILE_FP.write_text(dockerfile)
    print(f"🐳  Wrote Dockerfile")

    # =================================================================
    # === Build Docker Image
    # =================================================================

    print(f"🐳 ...  Building Docker image {image_tag} ...")
    utils.assert_docker_available()  # < Check docker
    utils.run_command(
        f"""docker build \\
        --tag {image_tag} \\
        --file {DOCKERFILE_FP} \\
        {PR_ROOT}
        """
    )

    size = utils.run_command(f"docker image ls | grep {commit_hash}").split()[
        -1
    ]

    print(f"🐳  Done building [Imagesize = {size}]")
    
    # =================================================================
    # === Next steps
    # =================================================================
    print("Next steps:")
    print(f"🚀  Run interactively:\tdocker run -it {image_tag}")
    print(f"👉  Push to ??:\tdocker push {image_tag}")
    print(
        f"🚮  Remove image:\tdocker image rm {image_tag}   (layers stay deduped)"
    )

    # %%
