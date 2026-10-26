#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${XDG_STATE_HOME:-}" ]; then STATE=$XDG_STATE_HOME; else STATE=${HOME:?HOME is required}/.local/state; fi
case "$STATE" in /*) ;; *) echo "XDG_STATE_HOME must be absolute." >&2; exit 2 ;; esac
TARGET=$STATE/buildben/installation/uninstall.sh
while [ "$TARGET" != / ]; do
    [ ! -L "$TARGET" ] || { echo "Lifecycle state must not be a symlink: $TARGET" >&2; exit 1; }
    TARGET=$(dirname -- "$TARGET")
done
SAVED=$STATE/buildben/installation/uninstall.sh
if [ -x "$SAVED" ] && [ "$(CDPATH= cd -- "$(dirname -- "$SAVED")" && pwd)/uninstall.sh" != "$HERE/uninstall.sh" ]; then exec "$SAVED" "$@"; fi
UV=
YES=false
DRY=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --uv) [ "$#" -ge 2 ] || { echo "--uv requires a path" >&2; exit 2; }; UV=$2; shift 2 ;;
        --yes) YES=true; shift ;;
        --dry-run) DRY=true; shift ;;
        *) echo "Without a saved receipt, recovery accepts only --uv PATH and --yes/--dry-run." >&2; exit 2 ;;
    esac
done
[ -n "$UV" ] || { echo "No lifecycle receipt; pass --uv PATH for package-only recovery." >&2; exit 2; }
case "$UV" in /*) ;; *) UV=$(command -v -- "$UV" || true) ;; esac
[ -n "$UV" ] || { echo "uv executable not found; run 'uv tool uninstall buildben' directly." >&2; exit 1; }
UV=$(CDPATH= cd -- "$(dirname -- "$UV")" && pwd)/$(basename -- "$UV")
PY=$("$UV" python find --system --no-project --no-python-downloads '>=3.12' 2>/dev/null) || { echo "No base Python available; run '\"$UV\" tool uninstall buildben' directly." >&2; exit 1; }
set -- uninstall --uv "$UV"
[ "$YES" = false ] || set -- "$@" --yes
[ "$DRY" = false ] || set -- "$@" --dry-run
exec "$PY" "$HERE/lifecycle.py" "$@"
