#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$HERE/src/<my_project>_dev/distribution/uninstall.sh" "$@"
