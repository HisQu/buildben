#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$HERE/src/buildben_dev/distribution/uninstall.sh" "$@"
