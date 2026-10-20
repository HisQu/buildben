#!/usr/bin/env bash

set -Eeuo pipefail

# == Application settings =====================================================
APP_DISTRIBUTION="<my_project>"
APP_COMMAND="<my_project>"
GITHUB_REPOSITORY="<github_username>/<my_project>"
GIT_REPOSITORY="https://github.com/<github_username>/<my_project>.git"
UV_VERSION="0.12.18"
BOOTSTRAP_TAG=""
BOOTSTRAP_HELPER_SHA256=""

# == Installer state ==========================================================
REQUESTED_MODE="auto"
MODE=""
VERSION=""
DEV_PATH=""
EXPLICIT_UV=""
ASSUME_YES=false
SKIP_CONFIG=false
SCRIPT_DIR=""
UV=""
UV_ORIGIN="missing"
TEMPORARY_DIRECTORY=""

usage() {
    cat <<EOF
Usage: install-linux-macos.sh [OPTIONS]

Default mode: install the latest published release. Use --version to select
another published release, --git for a developer install, or --dev for a
checkout synchronization.

Modes (choose at most one):
  --git                 Install from the Git repository.
  -d, --dev [PATH]      Sync an existing checkout. PATH defaults to the current directory.

Options:
  -v, --version VERSION Install a published release (0.1.0 becomes v0.1.0).
  --uv PATH             Use a specific uv executable.
  -y, --yes             Skip the installer confirmation.
  --skip-config         Skip configuration setup.
  -h, --help            Show this help.
EOF
}

fail() { printf '\nERROR: %s\n' "$*" >&2; return 1; }
on_exit() {
    local status=$?
    if [[ -n "$TEMPORARY_DIRECTORY" ]]; then rm -rf -- "$TEMPORARY_DIRECTORY"; fi
    if ((status != 0)); then printf '\nInstallation incomplete. Re-run the installer.\n' >&2; fi
}
trap on_exit EXIT
set_requested_mode() { if [[ "$REQUESTED_MODE" != auto ]]; then fail "Installation modes are mutually exclusive."; return 1; fi; REQUESTED_MODE="$1"; }
parse_args() {
    while (($#)); do
        case "$1" in
            --git) set_requested_mode git; shift ;;
            -d|--dev) set_requested_mode dev; if (($# >= 2)) && [[ "$2" != -* ]]; then DEV_PATH="$2"; shift; else DEV_PATH="."; fi; shift ;;
            -v|--version) (($# >= 2)) || { fail "$1 requires a version."; return 1; }; VERSION="$2"; shift 2 ;;
            --uv) (($# >= 2)) || { fail "--uv requires a path."; return 1; }; EXPLICIT_UV="$2"; shift 2 ;;
            -y|--yes) ASSUME_YES=true; shift ;;
            --skip-config) SKIP_CONFIG=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) fail "Unknown argument: $1"; return 1 ;;
        esac
    done
}

resolve_script_dir() {
    local asset_override="${!ASSET_ENV_NAME:-}"
    if [[ -n "$asset_override" ]]; then
        [[ -d "$asset_override" ]] || { fail "Installer asset directory does not exist: $asset_override"; return 1; }
        SCRIPT_DIR="$(cd -- "$asset_override" && pwd)"
    elif [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
        SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    fi
}
resolve_mode() {
    case "$REQUESTED_MODE" in
        git) MODE=git ;;
        dev) MODE=dev; [[ -n "$DEV_PATH" ]] || DEV_PATH="." ;;
        auto) MODE=release ;;
        *) fail "Unknown installation mode: $REQUESTED_MODE"; return 1 ;;
    esac
    if [[ "$MODE" == dev && ! -f "$DEV_PATH/pyproject.toml" ]]; then fail "No pyproject.toml found in development checkout: $DEV_PATH"; return 1; fi
}
set_uv_path() {
    local candidate="$1"
    if [[ "$candidate" != */* ]]; then candidate="$(command -v -- "$candidate" || true)"; fi
    [[ -n "$candidate" && -x "$candidate" ]] || { fail "uv executable does not exist or is not executable: $1"; return 1; }
    "$candidate" --version >/dev/null 2>&1 || { fail "The supplied executable does not appear to be uv: $candidate"; return 1; }
    UV="$candidate"
}
discover_uv() {
    if [[ -n "$EXPLICIT_UV" ]]; then set_uv_path "$EXPLICIT_UV"; UV_ORIGIN=explicit
    elif [[ -n "$SCRIPT_DIR" && -x "$SCRIPT_DIR/uv" && ! -d "$SCRIPT_DIR/uv" ]]; then set_uv_path "$SCRIPT_DIR/uv"; UV_ORIGIN=bundled
    elif [[ -n "$SCRIPT_DIR" && -x "$SCRIPT_DIR/uv/uv" ]]; then set_uv_path "$SCRIPT_DIR/uv/uv"; UV_ORIGIN=bundled
    elif command -v uv >/dev/null 2>&1; then set_uv_path "$(command -v uv)"; UV_ORIGIN=system
    else UV=""; UV_ORIGIN=missing; fi
}
install_permanent_uv() {
    command -v curl >/dev/null 2>&1 || { fail "curl is required to install uv. Install uv manually, then pass --uv PATH."; return 1; }
    local install_dir="${HOME}/.local/bin"
    mkdir -p "$install_dir"
    printf '\nInstalling uv %s permanently in %s...\n' "$UV_VERSION" "$install_dir"
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
    set_uv_path "$install_dir/uv"; UV_ORIGIN=per-user
}
print_plan() {
    printf '\n%s installation plan\n\n' "$APP_DISTRIBUTION"
    case "$MODE" in
        release|git) printf 'Mode:\n  Online published release installation\n\n1. Use %s uv.\n\n2. Validate and install the selected GitHub release.\n' "$UV_ORIGIN"; [[ -z "$VERSION" ]] || printf '   Version: %s\n' "$VERSION" ;;
        dev) printf 'Mode:\n  Development environment\n\nSynchronize checkout:\n   %s\n' "$(cd -- "$DEV_PATH" && pwd)" ;;
    esac
    if [[ "$SKIP_CONFIG" == true || "<configure_app>" != true ]]; then printf '\nConfiguration setup will be skipped.\n\n'; else printf '\nRun %s config setup after installation.\n\n' "$APP_COMMAND"; fi
}
read_terminal() { local response=""; [[ -r /dev/tty ]] || { fail "Interactive confirmation requires a terminal. Use --yes to continue."; return 1; }; printf '%s' "$1" >/dev/tty; IFS= read -r response </dev/tty || true; printf '%s' "$response"; }
confirm_plan() {
    [[ "$ASSUME_YES" == true ]] && return
    local response
    if [[ "$UV_ORIGIN" == missing ]]; then response="$(read_terminal 'Continue? uv will be installed permanently. Enter y/yes or n/no: ')"; else response="$(read_terminal 'Continue? [y/N]: ')"; fi
    case "${response,,}" in y|yes) return ;; n|no|"") printf '\nInstallation cancelled.\n'; exit 0 ;; *) fail "Expected y/yes or n/no."; return 1 ;; esac
}
update_tool_path() { if ! "$UV" tool update-shell; then printf '\nWARNING: uv could not update the tool executable PATH. Open a new shell or add the directory from `uv tool dir --bin` to PATH.\n' >&2; fi; }
git_ref() { if [[ -z "$VERSION" ]]; then printf main; elif [[ "$VERSION" == v* ]]; then printf '%s' "$VERSION"; else printf 'v%s' "$VERSION"; fi; }
install_from_git() {
    local ref source; ref="$(git_ref)"; source="git+${GIT_REPOSITORY}@${ref}"
    command -v git >/dev/null 2>&1 || { fail "Git is required for installation from the repository."; return 1; }
    git ls-remote --exit-code "$GIT_REPOSITORY" "$ref" >/dev/null || { fail "Cannot access Git ref '$ref'. Check Git installation and repository access."; return 1; }
    "$UV" tool install --force --refresh "$source"; update_tool_path
}
find_install_python() {
    local version candidate
    for version in 3.13 3.12; do
        if candidate="$("$UV" python find --no-project --no-python-downloads "$version" 2>/dev/null)"; then INSTALL_PYTHON="$candidate"; return 0; fi
    done
    "$UV" python install 3.12 || return 1
    if candidate="$("$UV" python find --no-project 3.12 2>/dev/null)"; then INSTALL_PYTHON="$candidate"; return 0; fi
    fail "uv could not provide its managed Python 3.12 interpreter."
}
install_from_release() {
    local helper="$SCRIPT_DIR/install_release.py" payload=false
    find_install_python || return 1
    if [[ ! -f "$helper" ]]; then
        [[ -n "$BOOTSTRAP_TAG" && -n "$BOOTSTRAP_HELPER_SHA256" ]] || { fail "No trusted adjacent helper or stamped release source is available."; return 1; }
        command -v curl >/dev/null 2>&1 || { fail "curl is required to download the stamped release helper."; return 1; }
        TEMPORARY_DIRECTORY="$(mktemp -d)"
        helper="$TEMPORARY_DIRECTORY/install_release.py"
        curl --fail --silent --show-error "https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/${BOOTSTRAP_TAG}/src/${APP_DISTRIBUTION//-/_}_dev/distribution/install_release.py" --output "$helper"
    fi
    if [[ -n "$BOOTSTRAP_HELPER_SHA256" ]]; then
        local actual; actual="$(shasum -a 256 "$helper" 2>/dev/null | cut -d' ' -f1 || sha256sum "$helper" | cut -d' ' -f1)"
        [[ "$actual" == "$BOOTSTRAP_HELPER_SHA256" ]] || { fail "Release helper digest does not match the stamped installer."; return 1; }
    fi
    local args=("$helper" --repository "$GITHUB_REPOSITORY" --distribution "$APP_DISTRIBUTION" --uv "$UV" --python "$INSTALL_PYTHON")
    if [[ -n "$VERSION" ]]; then args+=(--version "$VERSION")
    elif [[ -n "$BOOTSTRAP_TAG" ]]; then args+=(--version "$BOOTSTRAP_TAG"); fi
    if [[ -n "$SCRIPT_DIR" ]]; then
        local item found=false
        for item in release-manifest.json runtime-requirements.txt runtime-constraints.txt; do [[ ! -e "$SCRIPT_DIR/$item" ]] || found=true; done
        if [[ "$found" == true ]]; then args+=(--asset-dir "$SCRIPT_DIR"); payload=true; fi
    fi
    if [[ "$payload" == true ]]; then
        for item in release-manifest.json runtime-requirements.txt runtime-constraints.txt; do [[ -f "$SCRIPT_DIR/$item" ]] || { fail "Incomplete adjacent release payload: $item is missing."; return 1; }; done
    fi
    "$INSTALL_PYTHON" "${args[@]}"
    update_tool_path
}
installed_application() {
    local tool_bin executable; tool_bin="$("$UV" tool dir --bin)"; executable="$tool_bin/$APP_COMMAND"
    [[ -x "$executable" ]] || { fail "Installed command was not found: $executable"; return 1; }
    printf '%s' "$executable"
}
configure_installed_application() {
    [[ "$SKIP_CONFIG" == true || "<configure_app>" != true ]] && return
    local executable; executable="$(installed_application)"; printf '\nRunning configuration setup...\n'; "$executable" config setup
}
bootstrap_development() {
    local project; project="$(cd -- "$DEV_PATH" && pwd)"; printf '\nSynchronizing development environment...\n'
    (cd -- "$project"; if [[ -f uv.lock ]]; then "$UV" sync --locked; else "$UV" sync; fi; if [[ "$SKIP_CONFIG" != true && "<configure_app>" == true ]]; then if [[ -f uv.lock ]]; then "$UV" run --locked "$APP_COMMAND" config setup; else "$UV" run "$APP_COMMAND" config setup; fi; fi)
}
main() {
    parse_args "$@"; ASSET_ENV_NAME="${APP_DISTRIBUTION//-/_}"; ASSET_ENV_NAME="${ASSET_ENV_NAME^^}_INSTALLER_ASSET_DIR"
    resolve_script_dir; resolve_mode; discover_uv; print_plan; confirm_plan
    [[ "$UV_ORIGIN" != missing ]] || install_permanent_uv
    case "$MODE" in release) install_from_release; configure_installed_application ;; git) install_from_git; configure_installed_application ;; dev) bootstrap_development ;; esac
    printf '\n%s setup completed successfully.\n' "$APP_DISTRIBUTION"
    [[ "$MODE" == dev ]] || printf 'Open a new shell if `%s` is not available immediately.\n' "$APP_COMMAND"
}
main "$@"
