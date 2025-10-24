"""
bootstrap environment variables from .env files.
- Prioritizes direnv .envrc, if available
- Falls back to loading .env files via python-dotenv

About .env syntax:
- Usually only simple `KEY=VALUE` lines
- Usually comments, no `export`, no multiline values, no quotes
- For best compatibility, avoid `export` and use `${VAR}` syntax for interpolation!

python-dotenv:
- Interpolation works, but only with `${VAR}` syntax. Bare `$VAR` won’t expand. 
- Accepts `export KEY=...`, comments, and multiline values.
"""

# --- STD lib ---
import os, sys, json, shutil, subprocess, shlex
from pathlib import Path
from typing import Sequence

# --- Deps ---
from dotenv import load_dotenv  # < Installed via environs
from environs import Env, EnvError



# =====================================================================
# === env: Handle for connecting to the environment
# =====================================================================
env: Env = Env()  # < Create a global Env Wrapper (copies available variables)


# =====================================================================
# === Public Utilities
# =====================================================================

def import_vars(*names: str, allow_blank: bool = False) -> tuple[str, ...]:
    """
    Return the requested environment variables **in order**.
    - Raises RuntimeError if one or more are missing (or blank when allow_blank=False)
      and prints a friendly summary to stderr first.
    - If allow_blank=True, empty strings are accepted.
    """
    missing, vals = [], []
    for n in names:
        v = os.getenv(n, "")
        if (v == "" and not allow_blank) or v is None:
            missing.append(n)
        vals.append(v)
    if missing:
        msg = "Missing or invalid environment variables:\n  " + "\n  ".join(
            missing
        )
        print(msg, file=sys.stderr)
        raise RuntimeError(msg)
    return tuple(vals)


def source_shell_env(script: Path, *, quiet: bool = False) -> bool:
    """
    Source a shell script (e.g. .envrc.vars) in a child bash and import its environment.
    This lets us compute PROJECT_ROOT from "the file itself" without changing our own PWD.
    """
    bash = shutil.which("bash")
    if not bash or not script.exists():
        return False
    cmd = f"set -a; . {shlex.quote(str(script))}; env -0"
    try:
        out = subprocess.check_output([bash, "-lc", cmd])
    except subprocess.CalledProcessError:
        if not quiet:
            print(f"[env_boot.py] sourcing failed: {script}", file=sys.stderr)
        return False
    # --- Merge NUL-separated KEY=VAL pairs
    for pair in out.split(b"\x00"):
        if not pair:
            continue
        k, _, v = pair.partition(b"=")
        if k and _:
            os.environ[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    if not quiet:
        print(f"[env_boot.py] sourced shell env: {script}", file=sys.stderr)
    return True




# =====================================================================
# === load_env()
# =====================================================================

# --- Helpers -------------------------------------------------------


def _find_project_root(
    start: Path | None = None,
    sentinels: Sequence[str] = (".git", "pyproject.toml", "setup.py"),
    raise_error: bool = True,
) -> Path | None:
    """
    Returns environment variable "PROJECT_ROOT". Otherwise, falls back
    to Walk upward from *start* (or cwd) until we find a sentinel that
    marks the project root. Raises RuntimeError if none found.
    """
    ### Don't search if PROJECT_ROOT is already set
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        print("[env_boot.py] Using $PROJECT_ROOT from environment:", env_root, file=sys.stderr)
        return Path(env_root).resolve()  # !! Early exit
    ### Search upward for sentinels
    print("[env_boot.py] Searching for project root...", file=sys.stderr)
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if any((candidate / s).exists() for s in sentinels):
            return candidate  # !! Found!
    ### Nothing Found!
    m = f"Not inside a project; looked for {sentinels} starting at {here}"
    if raise_error:
        print(m, file=sys.stderr)
        raise RuntimeError(m)


def _apply_direnv_export_json(root: Path, quiet: bool = False) -> bool:
    """Run `direnv export json` and merge result into os.environ. Returns True if executed."""
    if not shutil.which("direnv"):
        return False  # < direnv binary missing
    try:
        if not quiet:
            print(f"[env_boot.py] Loading environment with direnv using {root}/.envrc", file=sys.stderr)
        # > Snapshot of current environment
        _env: dict[str, str] = os.environ.copy()
        if quiet:
            # > Empty string silences *all* log lines from direnv
            _env.setdefault("DIRENV_LOG_FORMAT", "")
        payload = subprocess.check_output(
            ["direnv", "export", "json"],
            cwd=str(root),
            text=True,
            env=_env,
            stderr=subprocess.DEVNULL if quiet else None,
        )
        if payload.strip():
            os.environ.update(json.loads(payload))
        # < empty payload means no diff, which is valid
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # > direnv binary missing
        # > .envrc not yet allowed
        # > export produced non-JSON because of an unexpected message
        if not quiet:
            print("[env_boot.py] direnv export failed", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        c = 1000
        snippet = (
            (payload[:c] + f" ... <truncated at {c} chars>")
            if payload and len(payload) > c
            else (payload or "No output")
        )
        raise RuntimeError(
            f"direnv export json returned non-JSON: {e}\n{snippet}"
        )



def _env_from_scratch(root, dotenvs: Path | str | Sequence[str]) -> None:
    """Build the environment from scratch when direnv is not used."""
    print(f"[env_boot.py] Loading environment with python using {dotenvs}", file=sys.stderr)
    # --- Manual env vars ---
    os.environ.setdefault("PROJECT_ROOT", str(root))
    os.environ.setdefault("PROJECT_NAME", root.name)
    # --- Layer multiple dotenvs: last file wins
    _dotenvs: list[str | Path] = (
        [dotenvs] if isinstance(dotenvs, (str, Path)) else list(dotenvs)
    )
    for dotenv in _dotenvs:
        p = Path(dotenv)
        if not p.is_absolute():
            p = Path(root / dotenv)
        if not p.exists():
            continue
        if p.suffix == ".sh":
            source_shell_env(p, quiet=True)
        else:
            load_dotenv(p, override=True)  # later files override earlier ones


# --- Main Interface of load_env --------------------------------------


def load_env(
    *,
    prefer_direnv: bool = True,
    dotenvs: Path | str | Sequence[str] = (
        ".env",
        ".env.sh",
        ".env.secret",
    ),
    quiet: bool = False,
) -> None:
    """Best-effort env setup for scripts and IPython."""
    if not quiet:
        print("-- [env_boot.py] Bootstrapping environment -------------------", file=sys.stderr)
    root = _find_project_root()
    # --- Prefer direnv if available; it evaluates .envrc correctly
    if prefer_direnv and _apply_direnv_export_json(root=root, quiet=quiet):
        return  # !! direnv loaded .envrc successfully
    # --- Fallback to loading .env files directly
    _env_from_scratch(root, dotenvs=dotenvs)


# => Demo =============================================================

def demo():
    pass
    # %%
    ### Find project root
    root = _find_project_root()
    print("Project root:", root)
    print("Project root '.':", _find_project_root(Path(".")))
    print("Project root None:", _find_project_root(None))

    # %%
    ### Load .envrc
    load_env()
    print("$PROJECT_ROOT", os.getenv("PROJECT_ROOT"))
    print("$BASE_URL", os.getenv("BASE_URL"))

    # %%
    # ?? Subsequent loads are automatically ignored
    load_env()

    # %%
    ### Import multiple vars at once
    a, b = import_vars("PROJECT_NAME", "PROJECT_ROOT")
    print("$PROJECT_NAME", a)
    print("$PROJECT_ROOT", b)



