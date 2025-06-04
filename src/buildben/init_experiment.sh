#!/usr/bin/env bash
# init_experiment.sh – create a fully reproducible experiment scaffold
# Usage: ./init_experiment.sh EXPERIMENT_NAME [--no-venv] [--no-freeze]

set -euo pipefail

#######################################
# === helper
#######################################
usage() {
    echo "Usage: $0 EXPERIMENT_NAME [--no-venv] [--no-freeze]" >&2
    exit 1
}

#######################################
# === parse arguments
#######################################
[ $# -lt 1 ] && usage

NAME=""
CREATE_VENV=true
DO_FREEZE=true

for arg in "$@"; do
    case "$arg" in
    --no-venv) CREATE_VENV=false ;;
    --no-freeze) DO_FREEZE=false ;;
    -* | --*) usage ;;
    *) NAME="$arg" ;;
    esac
done

[ -z "$NAME" ] && usage

#######################################
# === define paths
#######################################
DATE=$(date +%Y-%m-%d)
EXP_ROOT="experiments/${DATE}_${NAME}"

if [ -e "$EXP_ROOT" ]; then
    echo "Error: $EXP_ROOT already exists – choose a different name." >&2
    exit 2
fi

#######################################
# === create directory tree
#######################################
echo "Creating experiment folder structure at $EXP_ROOT"
mkdir -p "$EXP_ROOT"/{env,data,src,output}

#######################################
# === README + report template
#######################################
cat >"$EXP_ROOT/README.md" <<EOF
# Experiment – ${NAME}
*Date created:* ${DATE}

## Goal
Describe *what question you are answering* here.

## How to reproduce
\`\`\`bash
# activate venv (if you created one) or your workspace venv
source .venv/bin/activate      # or skip if you share one global env
bash run.sh                    # entry-point wraps src/run.py
\`\`\`

## Inputs
* **Data:** \`data/\` (tracked via DVC / symlink / copy)
* **Config:** \`src/config.yaml\` (add if needed)

## Outputs
Generated artifacts go to \`output/\`.

## Conclusion
Summarise findings in \`report.md\`.
EOF

touch "$EXP_ROOT/report.md"

#######################################
# === stub Python entry-point
#######################################
cat >"$EXP_ROOT/src/run.py" <<'PY'
"""
Minimal stub – replace with real experiment code.
"""
def main():
    print("Hello from the experiment stub!")

if __name__ == "__main__":
    main()
PY

#######################################
# === stub run.sh wrapper
#######################################
cat >"$EXP_ROOT/run.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# activate local venv if it exists
if [ -f "$DIR/.venv/bin/activate" ]; then
  source "$DIR/.venv/bin/activate"
fi
python "$DIR/src/run.py" "$@"
SH
chmod +x "$EXP_ROOT/run.sh"

#######################################
# === requirements files
#######################################
cat >"$EXP_ROOT/env/requirements.in" <<'EOF'
# Add loose dependencies here; next line is an example:
# venividiabbey @ editable ../../venividiabbey
EOF

if $DO_FREEZE; then
    if command -v pip-compile >/dev/null 2>&1; then
        echo "Freezing dependencies with pip-compile..."
        pip-compile "$EXP_ROOT/env/requirements.in" -o "$EXP_ROOT/env/requirements.txt"
    else
        echo "Skipping freeze – pip-compile not found. Install it with 'pip install pip-tools' if you need lockfiles." >&2
    fi
fi

#######################################
# === optional venv
#######################################
if $CREATE_VENV; then
    echo "Creating local virtual environment (.venv)..."
    python -m venv "$EXP_ROOT/.venv"
    # shellcheck disable=SC1090
    source "$EXP_ROOT/.venv/bin/activate"
    pip install -r "$EXP_ROOT/env/requirements.in" || true
fi

echo "✓ Experiment scaffold ready:"
tree -a -I '__pycache__|*.pyc' "$EXP_ROOT"
