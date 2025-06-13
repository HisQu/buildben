# !! Don't confuse this with the template!
# This is a collection of recipes callable from the CLI

# Allow `just deps-sync --upgrade --dry-run` pattern
set shell := ["bash", "-cu"]

# === Shortcuts / CI entrypoint =======================================

# Runs when you type just
default: 
    just --list


# === Installation ====================================================

# Use pipx to uninstall buildben and re-install it from pyproject.toml
reinstall:
    pipx uninstall buildben
    pipx install -e .
alias reins := reinstall

# Removes old test-project (bla_a); Re-Creates it
test-init:
    if [ -e "../bla_a" ]; then rm -rf "../bla_a"; fi
    echo "Creating ../bla_a"
    buildben init-proj \
        --name bla_a \
        --target-dir .. \
        --github-user markur4 \
        --git-init
alias tstin := test-init
