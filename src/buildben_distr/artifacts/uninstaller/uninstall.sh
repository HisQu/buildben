#!/bin/sh
set -eu
exec __APPRC_BASE_PYTHON__ "$(dirname -- "$0")/uninstall.py" --directory "$(dirname -- "$0")" "$@"
