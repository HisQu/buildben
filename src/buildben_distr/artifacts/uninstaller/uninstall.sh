#!/bin/sh
set -eu
exec __APPRC_BASE_PYTHON__ "$(dirname -- "$0")/management.py" uninstall --directory "$(dirname -- "$0")" "$@"
