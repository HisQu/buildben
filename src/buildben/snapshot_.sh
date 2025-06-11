#!/usr/bin/env bash
set -euo pipefail

# --- Config ---------------------------------------------------------
BASE_IMAGE="python:3.12-slim"       # tiny, official image 
PKG_NAME="$(basename "$(git rev-parse --show-toplevel)")"
TODAY=$(date +%Y-%m-%d)
EXP_TAG="$(git rev-parse --short HEAD)"     # commit hash 
EXP_DIR="experiments/${TODAY}_"



# --- Guard rails ----------------------------------------------------
[[ $# -gt 0 ]] && { echo "Usage: buildben snapshot  (no args)"; exit 2; }
[[ -d "$EXP_DIR" ]] || { echo "✗ Experiment folder '$EXP_DIR' missing"; exit 3; }

# --- Step 1: freeze deps -------------------------------------------
echo "• Freezing dependencies …"
pip-compile --all-extras pyproject.toml \
            "$EXP_DIR/env/exp-requirements.in" \
            -o "$EXP_DIR/env/requirements.lock"                
echo "✓ requirements.lock written"

# --- Step 2: record commit -----------------------------------------
echo "$EXP_TAG" > "$EXP_DIR/experiment.env"
echo "COMMIT=$EXP_TAG" >> "$EXP_DIR/experiment.env"

# --- Step 3: build docker image ------------------------------------
cat > "$EXP_DIR/Dockerfile" <<EOF
FROM ${BASE_IMAGE}
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r env/requirements.lock          # all pins
ENTRYPOINT ["python", "run.py"]
EOF

docker build -t "${PKG_NAME}:${EXP_TAG}" "$EXP_DIR"               
echo "✓ Docker image ${PKG_NAME}:${EXP_TAG} built"

# --- Optional: run with DVC ----------------------------------------
if command -v dvc &>/dev/null; then
  echo "• Tracking run with DVC …"
  dvc exp run -S "docker_tag=${PKG_NAME}:${EXP_TAG}"               
fi

echo "✅ Snapshot complete → $EXP_DIR"