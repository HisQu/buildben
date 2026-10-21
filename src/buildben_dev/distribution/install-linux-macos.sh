#!/usr/bin/env bash

set -Eeuo pipefail

APP_DISTRIBUTION="buildben"
APP_COMMAND="buildben"
GITHUB_REPOSITORY="HisQu/buildben"
UV_VERSION="0.12.18"
GITHUB_CLIENT="curl"
VERSION=""
EXPLICIT_UV=""
ASSUME_YES=false
SKIP_CONFIG=false
UV=""
UV_ORIGIN="missing"
INSTALL_PYTHON=""
TEMPORARY_DIRECTORY=""

usage() {
    cat <<EOF
Usage: install-linux-macos.sh [OPTIONS]

Install the latest published stable source distribution, or select one version.

Options:
  -v, --version VERSION Install a published release (0.1.0 becomes v0.1.0).
  --github-client CLIENT Use public curl or authenticated gh (default: curl).
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

parse_args() {
    while (($#)); do
        case "$1" in
            -v|--version) (($# >= 2)) || { fail "$1 requires a version."; return 1; }; VERSION="$2"; shift 2 ;;
            --github-client) (($# >= 2)) || { fail "--github-client requires curl or gh."; return 1; }; GITHUB_CLIENT="$2"; shift 2 ;;
            --uv) (($# >= 2)) || { fail "--uv requires a path."; return 1; }; EXPLICIT_UV="$2"; shift 2 ;;
            -y|--yes) ASSUME_YES=true; shift ;;
            --skip-config) SKIP_CONFIG=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) fail "Unknown argument: $1"; return 1 ;;
        esac
    done
    [[ "$GITHUB_CLIENT" == curl || "$GITHUB_CLIENT" == gh ]] || { fail "Invalid --github-client '$GITHUB_CLIENT'; choose curl or gh."; return 1; }
    if [[ -n "$VERSION" ]]; then
        VERSION="${VERSION#v}"
        [[ "$VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || { fail "Invalid release version: $VERSION"; return 1; }
        VERSION="v$VERSION"
    fi
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
confirm_plan() {
    printf '\n%s installation plan\nMode: published stable source distribution\nTransport: %s\nuv: %s\n' "$APP_DISTRIBUTION" "$GITHUB_CLIENT" "$UV_ORIGIN"
    [[ -z "$VERSION" ]] || printf 'Version: %s\n' "$VERSION"
    if [[ "$ASSUME_YES" == true ]]; then return; fi
    [[ -r /dev/tty ]] || { fail "Interactive confirmation requires a terminal. Use --yes to continue."; return 1; }
    local response
    printf 'Continue? [y/N]: ' >/dev/tty
    IFS= read -r response </dev/tty || true
    case "${response,,}" in y|yes) ;; *) printf '\nInstallation cancelled.\n'; exit 0 ;; esac
}
update_tool_path() { if ! "$UV" tool update-shell; then printf '\nWARNING: uv could not update the tool executable PATH. Open a new shell or add the directory from `uv tool dir --bin` to PATH.\n' >&2; fi; }

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
    find_install_python || return 1
    TEMPORARY_DIRECTORY="$(mktemp -d)"
    "$INSTALL_PYTHON" - "$UV" "$GITHUB_CLIENT" "$GITHUB_REPOSITORY" "$VERSION" "$TEMPORARY_DIRECTORY" "$APP_DISTRIBUTION" <<'PY'
import json, re, subprocess, sys, tarfile
from pathlib import Path, PurePosixPath
uv, client, repo, requested, temp, distribution = sys.argv[1:]
root = Path(temp)
version_re = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
def normalize(value): return re.sub(r"[-_.]+", "_", value).lower()
def gh_api(path): return subprocess.run(["gh", "api", path], check=True, text=True, capture_output=True).stdout
def public_json(url): return subprocess.run(["curl", "-fsSL", url], check=True, text=True, capture_output=True).stdout
if requested:
    if not re.fullmatch(r"v" + version_re.pattern[1:-1], requested): raise SystemExit("Malformed release tag")
    endpoint = f"/repos/{repo}/releases/tags/{requested}"
    response = gh_api(endpoint) if client == "gh" else public_json(f"https://api.github.com{endpoint}")
else:
    endpoint = f"/repos/{repo}/releases/latest"
    response = gh_api(endpoint) if client == "gh" else public_json(f"https://api.github.com{endpoint}")
try: release = json.loads(response)
except (ValueError, TypeError) as exc: raise SystemExit("GitHub returned invalid release JSON") from exc
if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False: raise SystemExit("Selected GitHub release is not a published stable release")
tag = release.get("tag_name")
if not isinstance(tag, str) or not re.fullmatch(r"v" + version_re.pattern[1:-1], tag): raise SystemExit("GitHub release has a malformed tag")
if requested and tag != requested: raise SystemExit("GitHub returned a different release tag")
version = tag[1:]
assets = release.get("assets")
if not isinstance(assets, list): raise SystemExit("GitHub release has no asset list")
matching = []
for asset in assets:
    if not isinstance(asset, dict): continue
    name, url = asset.get("name"), asset.get("browser_download_url")
    if not isinstance(name, str) or not isinstance(url, str): continue
    if name.endswith(".tar.gz") and name[:-7].endswith("-" + version) and normalize(name[:-7][:-(len(version)+1)]) == normalize(distribution): matching.append((name, url))
if len(matching) != 1: raise SystemExit(f"Expected exactly one matching source distribution, found {len(matching)}")
name, url = matching[0]
archive = root / name
if client == "gh": subprocess.run(["gh", "release", "download", tag, "--repo", repo, "--pattern", name, "--dir", temp], check=True)
else: subprocess.run(["curl", "-fsSL", url, "--output", str(archive)], check=True)
if not archive.is_file() or archive.stat().st_size == 0: raise SystemExit("Source distribution download is empty")
with tarfile.open(archive, "r:gz") as package:
    members = package.getmembers()
    roots = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\\" in member.name or re.match(r"^[A-Za-z]:", member.name): raise SystemExit("Source archive contains an unsafe path")
        if member.issym() or member.islnk() or not (member.isdir() or member.isfile()): raise SystemExit("Source archive contains links or special files")
        if path.parts: roots.add(path.parts[0])
    if len(roots) != 1: raise SystemExit("Source archive must contain exactly one project root")
    (root / "source").mkdir()
    package.extractall(root / "source", filter="data")
project_root = root / "source" / next(iter(roots))
pyproject, lock = project_root / "pyproject.toml", project_root / "uv.lock"
if not pyproject.is_file() or not lock.is_file(): raise SystemExit("Release source must contain pyproject.toml and uv.lock; this release is not installable")
import tomllib
with pyproject.open("rb") as stream: project = tomllib.load(stream).get("project", {})
if normalize(project.get("name", "")) != normalize(distribution) or project.get("version") != version: raise SystemExit("Source project metadata does not match selected release")
subprocess.run([uv, "export", "--locked", "--no-dev", "--no-default-groups", "--no-emit-project", "--format", "requirements.txt", "--output-file", str(root / "runtime-requirements.txt")], cwd=project_root, check=True)
subprocess.run([uv, "tool", "install", "--force", "--refresh", "--python", sys.executable, "--with-requirements", str(root / "runtime-requirements.txt"), str(project_root)], check=True)
PY
    update_tool_path
}

installed_application() {
    local tool_bin executable; tool_bin="$($UV tool dir --bin)"; executable="$tool_bin/$APP_COMMAND"
    [[ -x "$executable" ]] || { fail "Installed command was not found: $executable"; return 1; }
    printf '%s' "$executable"
}
configure_installed_application() {
    [[ "$SKIP_CONFIG" == true ]] && return
    local executable; executable="$(installed_application)"; printf '\nRunning configuration setup...\n'; "$executable" config setup
}

main() {
    parse_args "$@"
    discover_uv
    confirm_plan
    [[ "$UV_ORIGIN" != missing ]] || install_permanent_uv
    install_from_release
    configure_installed_application
    printf '\n%s setup completed successfully.\n' "$APP_DISTRIBUTION"
    printf 'Open a new shell if `%s` is not available immediately.\n' "$APP_COMMAND"
}
main "$@"