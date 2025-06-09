# !! Don't confuse this with the template!
# This is a collection of recipes callable from the CLI

# Allow `just deps-sync --upgrade --dry-run` pattern
set shell := ["bash", "-cu"]

# === Shortcuts / CI entrypoint =======================================

# Runs when you type just
default: 
    just --list


# === Installation ====================================================

reinstall:
    pipx uninstall buildben
    pipx install -e .
    
test_init_proj:
    [ -d "../bla_a" ] && rm -rf "../bla_a"
    echo "Creating ../bla_a"
    buildben init-proj \
        -n bla_a \
        -t .. \
        -u markur4
