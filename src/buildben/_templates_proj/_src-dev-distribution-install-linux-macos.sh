#!/usr/bin/env bash

set -Eeuo pipefail


# == Application settings =====================================================

APP_DISTRIBUTION="<my_project>"
APP_COMMAND="<my_project>"
REPOSITORY="https://github.com/<github_username>/<my_project>.git"
DEFAULT_REF="main"
UV_VERSION="0.12.18"
ASSET_ENV_NAME="<MY_PROJECT>_INSTALLER_ASSET_DIR"


# == Installer state ==========================================================

REQUESTED_MODE="auto"
MODE=""
VERSION=""
WHEEL_PATH=""
DEV_PATH=""
EXPLICIT_UV=""
ASSUME_YES=false
SKIP_CONFIG=false
SCRIPT_DIR=""
UV=""
UV_ORIGIN="missing"
OFFLINE_PYTHON=""
LOCAL_WHEELS=()


# == Utility functions ========================================================

usage() {
    cat <<EOF
Usage: install-linux-macos.sh [OPTIONS]

Default mode: install one matching wheel beside this installer, if present;
otherwise install from Git. A streamed script uses Git mode.

Modes (choose at most one):
  --git                 Install from the Git repository.
  -w, --wheel [PATH]    Install from a local wheelhouse. If PATH is omitted,
                        detect the application wheel beside this installer.
  -d, --dev [PATH]      Sync an existing checkout. PATH defaults to the
                        current directory.

Options:
  -v, --version VERSION Install a Git tag (0.1.0 becomes v0.1.0).
  --uv PATH             Use a specific uv executable.
  -y, --yes             Skip the installer confirmation.
  --skip-config         Skip "$APP_COMMAND config setup".
  -h, --help            Show this help.
EOF
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    return 1
}

on_exit() {
    local status=$?
    if ((status != 0)); then
        printf '\nInstallation incomplete. Re-run the installer.\n' >&2
    fi
}

trap on_exit EXIT


# == Argument parsing =========================================================

set_requested_mode() {
    if [[ "$REQUESTED_MODE" != "auto" ]]; then
        fail "Installation modes are mutually exclusive."
        return 1
    fi
    REQUESTED_MODE="$1"
}

parse_args() {
    while (($#)); do
        case "$1" in
            --git)
                set_requested_mode git
                shift
                ;;
            -w|--wheel)
                set_requested_mode wheel
                if (($# >= 2)) && [[ "$2" != -* ]]; then
                    WHEEL_PATH="$2"
                    shift
                fi
                shift
                ;;
            -d|--dev)
                set_requested_mode dev
                if (($# >= 2)) && [[ "$2" != -* ]]; then
                    DEV_PATH="$2"
                    shift
                else
                    DEV_PATH="."
                fi
                shift
                ;;
            -v|--version)
                (($# >= 2)) || { fail "$1 requires a version."; return 1; }
                VERSION="$2"
                shift 2
                ;;
            --uv)
                (($# >= 2)) || { fail "--uv requires a path."; return 1; }
                EXPLICIT_UV="$2"
                shift 2
                ;;
            -y|--yes)
                ASSUME_YES=true
                shift
                ;;
            --skip-config)
                SKIP_CONFIG=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                fail "Unknown argument: $1"
                return 1
                ;;
        esac
    done
}


# == Installer location and mode =============================================

resolve_script_dir() {
    local asset_override="${!ASSET_ENV_NAME:-}"
    if [[ -n "$asset_override" ]]; then
        [[ -d "$asset_override" ]] || {
            fail "Installer asset directory does not exist: $asset_override"
            return 1
        }
        SCRIPT_DIR="$(cd -- "$asset_override" && pwd)"
    elif [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
        SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    fi
}

collect_local_wheels() {
    LOCAL_WHEELS=()
    [[ -n "$SCRIPT_DIR" ]] || return

    local prefix directory wheel
    prefix="$(printf '%s' "$APP_DISTRIBUTION" | tr '[:upper:]' '[:lower:]')"
    prefix="${prefix//-/_}"
    shopt -s nullglob
    for directory in "$SCRIPT_DIR" "$SCRIPT_DIR/wheels"; do
        [[ -d "$directory" ]] || continue
        for wheel in "$directory"/"$prefix"-*.whl; do
            [[ -f "$wheel" ]] || continue
            LOCAL_WHEELS+=("$(cd -- "$(dirname -- "$wheel")" && pwd)/$(basename -- "$wheel")")
        done
    done
    shopt -u nullglob
}

select_detected_wheel() {
    collect_local_wheels
    if ((${#LOCAL_WHEELS[@]} != 1)); then
        fail "Expected exactly one ${APP_DISTRIBUTION} wheel beside this installer."
        return 1
    fi
    WHEEL_PATH="${LOCAL_WHEELS[0]}"
}

resolve_mode() {
    case "$REQUESTED_MODE" in
        git) MODE="git" ;;
        dev)
            MODE="dev"
            [[ -n "$DEV_PATH" ]] || DEV_PATH="."
            ;;
        wheel)
            MODE="wheel"
            [[ -n "$WHEEL_PATH" ]] || select_detected_wheel
            ;;
        auto)
            collect_local_wheels
            if ((${#LOCAL_WHEELS[@]} == 1)); then
                MODE="wheel"
                WHEEL_PATH="${LOCAL_WHEELS[0]}"
            else
                MODE="git"
            fi
            ;;
        *)
            fail "Unknown installation mode: $REQUESTED_MODE"
            return 1
            ;;
    esac

    if [[ "$MODE" != "git" && -n "$VERSION" ]]; then
        fail "--version is only valid for Git installation."
        return 1
    fi
    if [[ "$MODE" == "wheel" && ! -f "$WHEEL_PATH" ]]; then
        fail "Wheel does not exist: $WHEEL_PATH"
        return 1
    fi
    if [[ "$MODE" == "dev" && ! -f "$DEV_PATH/pyproject.toml" ]]; then
        fail "No pyproject.toml found in development checkout: $DEV_PATH"
        return 1
    fi
}


# == uv discovery and bootstrap ==============================================

set_uv_path() {
    local candidate="$1"
    if [[ "$candidate" != */* ]]; then
        candidate="$(command -v -- "$candidate" || true)"
    fi
    [[ -n "$candidate" && -x "$candidate" ]] || {
        fail "uv executable does not exist or is not executable: $1"
        return 1
    }
    "$candidate" --version >/dev/null 2>&1 || {
        fail "The supplied executable does not appear to be uv: $candidate"
        return 1
    }
    UV="$candidate"
}

discover_uv() {
    if [[ -n "$EXPLICIT_UV" ]]; then
        set_uv_path "$EXPLICIT_UV"
        UV_ORIGIN="explicit"
    elif [[ -n "$SCRIPT_DIR" && -x "$SCRIPT_DIR/uv" && ! -d "$SCRIPT_DIR/uv" ]]; then
        set_uv_path "$SCRIPT_DIR/uv"
        UV_ORIGIN="bundled"
    elif [[ -n "$SCRIPT_DIR" && -x "$SCRIPT_DIR/uv/uv" ]]; then
        set_uv_path "$SCRIPT_DIR/uv/uv"
        UV_ORIGIN="bundled"
    elif command -v uv >/dev/null 2>&1; then
        set_uv_path "$(command -v uv)"
        UV_ORIGIN="system"
    else
        UV=""
        UV_ORIGIN="missing"
    fi
}

install_permanent_uv() {
    [[ "$MODE" != "wheel" ]] || {
        fail "Offline installation needs local uv. Use --uv PATH or install uv first."
        return 1
    }
    command -v curl >/dev/null 2>&1 || {
        fail "curl is required to install uv. Install uv manually, then pass --uv PATH."
        return 1
    }
    local install_dir="${HOME}/.local/bin"
    mkdir -p "$install_dir"
    printf '\nInstalling uv %s permanently in %s...\n' "$UV_VERSION" "$install_dir"
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" \
        | env UV_INSTALL_DIR="$install_dir" sh
    set_uv_path "$install_dir/uv"
    UV_ORIGIN="per-user"
}


# == Plan and confirmation ====================================================

git_ref() {
    if [[ -z "$VERSION" ]]; then
        printf '%s' "$DEFAULT_REF"
    elif [[ "$VERSION" == v* ]]; then
        printf '%s' "$VERSION"
    else
        printf 'v%s' "$VERSION"
    fi
}

print_plan() {
    printf '\n%s installation plan\n\n' "$APP_DISTRIBUTION"
    case "$MODE" in
        git)
            printf 'Mode:\n  Online Git installation\n\n'
            printf '1. Use %s uv.\n' "$UV_ORIGIN"
            if [[ "$UV_ORIGIN" == "missing" ]]; then
                printf '   If you continue, uv %s will be installed permanently in %s/.local/bin.\n' "$UV_VERSION" "$HOME"
            else
                printf '   %s\n' "$UV"
            fi
            printf '\n2. Install or update %s with uv tool install.\n' "$APP_DISTRIBUTION"
            printf '   Source: %s\n   Git ref: %s\n\n' "$REPOSITORY" "$(git_ref)"
            ;;
        wheel)
            printf 'Mode:\n  Offline wheel installation\n\n'
            printf '1. Use local %s uv: %s\n' "$UV_ORIGIN" "${UV:-not found}"
            printf '2. Install the wheel and dependencies from local files only.\n'
            printf '   Network access, Python downloads, and source builds are disabled.\n\n'
            ;;
        dev)
            printf 'Mode:\n  Development environment\n\n'
            printf '1. Use %s uv.\n' "$UV_ORIGIN"
            if [[ "$UV_ORIGIN" == "missing" ]]; then
                printf '   If you continue, uv %s will be installed permanently in %s/.local/bin.\n' "$UV_VERSION" "$HOME"
            else
                printf '   %s\n' "$UV"
            fi
            printf '\n2. Synchronize the checkout with uv sync:\n   %s\n\n' "$(cd -- "$DEV_PATH" && pwd)"
            ;;
    esac
    if [[ "$SKIP_CONFIG" == true ]]; then
        printf '3. Skip %s config setup.\n\n' "$APP_COMMAND"
    elif [[ "$MODE" == "dev" ]]; then
        printf '3. Run %s config setup in the checkout.\n\n' "$APP_COMMAND"
    else
        printf '3. Run %s config setup after installation.\n\n' "$APP_COMMAND"
    fi
}

read_terminal() {
    local prompt="$1" response=""
    [[ -r /dev/tty ]] || {
        fail "Interactive confirmation requires a terminal. Use --yes to continue."
        return 1
    }
    printf '%s' "$prompt" >/dev/tty
    IFS= read -r response </dev/tty || true
    printf '%s' "$response"
}

confirm_plan() {
    if [[ "$ASSUME_YES" == true ]]; then
        [[ "$MODE" != "wheel" || "$UV_ORIGIN" != "missing" ]] || {
            fail "Offline installation needs local uv. Use --uv PATH or install uv first."
            return 1
        }
        return
    fi

    local response
    if [[ "$UV_ORIGIN" == "missing" && "$MODE" == "wheel" ]]; then
        response="$(read_terminal 'Enter a path to local uv, or n/no to cancel: ')"
        case "${response,,}" in
            n|no|"") printf '\nInstallation cancelled.\n'; exit 0 ;;
            *) set_uv_path "$response"; UV_ORIGIN="interactive" ;;
        esac
    elif [[ "$UV_ORIGIN" == "missing" ]]; then
        response="$(read_terminal 'Continue? uv will be installed permanently. Enter y/yes or n/no: ')"
        case "${response,,}" in
            y|yes) return ;;
            n|no|"") printf '\nInstallation cancelled.\n'; exit 0 ;;
            *) fail "Enter y/yes or n/no."; return 1 ;;
        esac
    else
        response="$(read_terminal 'Continue? [y/N]: ')"
        case "${response,,}" in
            y|yes) return ;;
            n|no|"") printf '\nInstallation cancelled.\n'; exit 0 ;;
            *) fail "Expected y/yes or n/no."; return 1 ;;
        esac
    fi
}


# == Installation ============================================================

update_tool_path() {
    if ! "$UV" tool update-shell; then
        printf '\nWARNING: uv could not update the tool executable PATH. Open a new shell or add the directory from `uv tool dir --bin` to PATH.\n' >&2
    fi
}

install_from_git() {
    local ref source
    ref="$(git_ref)"
    source="git+${REPOSITORY}@${ref}"
    command -v git >/dev/null 2>&1 || {
        fail "Git is required for installation from the repository."
        return 1
    }
    printf '\nChecking access to %s at %s...\n' "$REPOSITORY" "$ref"
    git ls-remote --exit-code "$REPOSITORY" "$ref" >/dev/null || {
        fail "Cannot access Git ref '$ref'. Check Git installation and repository access."
        return 1
    }
    printf '\nInstalling %s from Git...\n' "$APP_DISTRIBUTION"
    "$UV" tool install --force --refresh "$source"
    update_tool_path
}

install_from_wheel() {
    local wheel_dir candidate version
    wheel_dir="$(cd -- "$(dirname -- "$WHEEL_PATH")" && pwd)"
    for version in 3.13 3.12; do
        if candidate="$("$UV" python find --no-project --no-python-downloads "$version" 2>/dev/null)"; then
            OFFLINE_PYTHON="$candidate"
            break
        fi
    done
    [[ -n "$OFFLINE_PYTHON" ]] || {
        fail "Offline installation requires an existing Python 3.12 or 3.13 interpreter."
        return 1
    }
    local args=(tool install --force --offline --no-index --no-python-downloads --no-build --python "$OFFLINE_PYTHON" --find-links "$wheel_dir")
    if [[ -n "$SCRIPT_DIR" && -d "$SCRIPT_DIR/wheels" && "$SCRIPT_DIR/wheels" != "$wheel_dir" ]]; then
        args+=(--find-links "$SCRIPT_DIR/wheels")
    fi
    args+=("$WHEEL_PATH")
    printf '\nInstalling %s from local wheels...\n' "$APP_DISTRIBUTION"
    "$UV" "${args[@]}"
    update_tool_path
}

installed_application() {
    local tool_bin executable
    tool_bin="$("$UV" tool dir --bin)"
    executable="$tool_bin/$APP_COMMAND"
    [[ -x "$executable" ]] || {
        fail "Installed command was not found: $executable"
        return 1
    }
    printf '%s' "$executable"
}

configure_installed_application() {
    [[ "$SKIP_CONFIG" == true ]] && return
    local executable
    executable="$(installed_application)"
    printf '\nRunning configuration setup...\n'
    "$executable" config setup
}

bootstrap_development() {
    local project
    project="$(cd -- "$DEV_PATH" && pwd)"
    printf '\nSynchronizing development environment...\n'
    (
        cd -- "$project"
        if [[ -f uv.lock ]]; then
            "$UV" sync --locked
        else
            "$UV" sync
        fi
        if [[ "$SKIP_CONFIG" != true ]]; then
            if [[ -f uv.lock ]]; then
                "$UV" run --locked "$APP_COMMAND" config setup
            else
                "$UV" run "$APP_COMMAND" config setup
            fi
        fi
    )
}


# == Main ====================================================================

main() {
    parse_args "$@"
    resolve_script_dir
    resolve_mode
    discover_uv
    print_plan
    confirm_plan
    if [[ "$UV_ORIGIN" == "missing" ]]; then
        install_permanent_uv
    fi
    case "$MODE" in
        git) install_from_git; configure_installed_application ;;
        wheel) install_from_wheel ;;
        dev) bootstrap_development ;;
    esac
    printf '\n%s setup completed successfully.\n' "$APP_DISTRIBUTION"
    if [[ "$MODE" != "dev" ]]; then
        printf 'Open a new shell if `%s` is not available immediately.\n' "$APP_COMMAND"
    fi
}

main "$@"
