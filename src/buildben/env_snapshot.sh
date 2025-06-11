#!/usr/bin/env bash
#
# Snapshot a Python project into:
#   - <target_dir>/requirements.lock
#   - <target_dir>/experiment.env
#   - Docker image  <proj_name>:<commit>
#
# Arguments ---------------------------------------------------------------
#   --proj_name  (-n)   : image / tag base, e.g. "myproj"
#   --proj_root  (-r)   : path to project root containing .direnv / pyproject.toml
#   --target_dir (-t)   : directory to write lock & env files
#   --py_base    (-b)   : base image (default "python:3.12-slim")
# -------------------------------------------------------------------------

set -Eeuo pipefail

# ---------- defaults ----------------------------------------------------
PY_BASE="python:3.12-slim"
# -------------------------------------------------------------------------

usage() {
    echo "Usage: $0 --proj_name NAME --proj_root PATH --target_dir PATH [--py_base IMAGE]"
    exit 1
}

# --- simple getopt parsing ----------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
    -n | --proj_name)
        PROJ_NAME="$2"
        shift 2
        ;;
    -r | --proj_root)
        PROJ_ROOT="$2"
        shift 2
        ;;
    -t | --target_dir)
        TARGET_DIR="$2"
        shift 2
        ;;
    -b | --py_base)
        PY_BASE="$2"
        shift 2
        ;;
    -h | --help) usage ;;
    *)
        echo "Unknown option $1"
        usage
        ;;
    esac
done

[[ -z "${PROJ_NAME:-}" || -z "${PROJ_ROOT:-}" || -z "${TARGET_DIR:-}" ]] && usage

LOCK_FILE="$TARGET_DIR/requirements.lock"
ENV_FILE="$TARGET_DIR/experiment.env"

mkdir -p "$TARGET_DIR"

# === snapshot code ===================================================
pushd "$PROJ_ROOT" >/dev/null

# --- Capture Commit Hash ---------------------------------------------
COMMIT_HASH=$(git rev-parse --short HEAD)
timepoint=$(git show --format=%cd --date=iso ${COMMIT_HASH} | head -n 1)
echo "🔖  Using Commit: $COMMIT_HASH ($timepoint)"

# --- Freeze the live venv --------------------------------------------
# !!
# pip freeze >"$LOCK_FILE" 
pip-compile --generate-hashes --extra dev pyproject.toml -o "$LOCK_FILE"
echo "📌  Environment pip frozen to $LOCK_FILE"

# --- Write experiment.env --------------------------------------------
cat >"$ENV_FILE" <<EOF
COMMIT_HASH=$COMMIT_HASH
LOCK_FILE=$(basename "$LOCK_FILE")
EOF
echo "🔖  Wrote $ENV_FILE (for DVC, MLflow, etc.)"

IMAGE_TAG="${PROJ_NAME}:${COMMIT_HASH}"

# --- Write & Build Dockerfile ----------------------------------------
docker build \
    --build-arg PY_BASE="$PY_BASE" \
    --build-arg COMMIT_HASH="$COMMIT_HASH" \
    --build-arg LOCK_FILE="$(basename "$LOCK_FILE")" \
    -t "$IMAGE_TAG" -f - . <<'DOCKERFILE'
# syntax=docker/dockerfile:1

ARG PY_BASE
ARG LOCK_FILE
ARG COMMIT_HASH
FROM ${PY_BASE}

### Install the pinned deps from requirements.lock
COPY ${LOCK_FILE} /app/requirements.lock
RUN pip install --require-hashes --no-cache-dir -r /app/requirements.lock

### Copy the complete repo & continue working in /app
COPY . /app
WORKDIR /app

### Force-checkout the exact commit
RUN git -C . checkout ${COMMIT_HASH} && pip install -e .
CMD ["python", "-m", "your_pkg.cli"]
DOCKERFILE

echo "🐳  Built Docker image $IMAGE_TAG"
echo "👉  Push with:  docker push $IMAGE_TAG"
echo "🧹  Remove local copy: docker image rm $IMAGE_TAG   (layers stay deduped)"

popd >/dev/null
