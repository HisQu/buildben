# .env.sh
# shellcheck shell=bash
# Compute PROJECT_ROOT from the location of THIS file.
# Works in bash and zsh; POSIX sh/dash can't do this reliably when sourced.

# === Get the path of this sourced file ===============================
if [ -n "${BASH_SOURCE[0]:-}" ]; then
  _SELF="${BASH_SOURCE[0]}"              # < bash: path even when sourced
elif [ -n "${ZSH_VERSION:-}" ]; then
  _SELF="${(%):-%N}"                     # < zsh: path even when sourced
else
  _SELF="${0}"                           # < best-effort for other shells
fi
# > Normalise to absolute Path
_SELF_DIR="$(cd -- "$(dirname -- "$_SELF")" && pwd -P)"


# === Export Environment Variables ====================================
# > Syntax: export VAR_NAME="value"
# > Syntax: export VAR_NAME="${VAR_NAME:-fallback_value}"
export PROJECT_ROOT="${PROJECT_ROOT:-$_SELF_DIR}"
export PROJECT_NAME="${PROJECT_NAME:-$(basename -- "$PROJECT_ROOT")}"
# export MY_VAR="some Path"