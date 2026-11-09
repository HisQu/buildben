#!/bin/sh
set -eu
HOME=${HOME:?HOME is required to locate the installation}
case "$(uname -s)" in
  Darwin) DIRECTORY="$HOME/Library/Application Support/buildben/installation" ;;
  *)
    case "${XDG_DATA_HOME-}" in
      /*) DATA_HOME=$XDG_DATA_HOME ;;
      *) DATA_HOME="$HOME/.local/share" ;;
    esac
    DIRECTORY="$DATA_HOME/buildben/installation" ;;
esac
exec "$DIRECTORY/uninstall.sh" "$@"
