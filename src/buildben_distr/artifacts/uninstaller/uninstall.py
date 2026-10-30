#!/usr/bin/env python3
"""Dispatch saved uninstall without consulting ambient uv or provisioning on preview."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

def _installation_directory(app_id):
    import re
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", app_id) is None:
        raise ValueError("Invalid application identity.")
    home = Path(os.environ.get("USERPROFILE" if os.name == "nt" else "HOME") or Path.home())
    if not home.is_absolute():
        raise ValueError("Native home path must be absolute.")
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        return local / app_id / "installation"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / app_id / "installation"
    data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    if not data.is_absolute():
        data = home / ".local" / "share"
    return data / app_id / "installation"


BASE_PYTHON = "__APPRC_BASE_PYTHON__"

def _base_python(target_prefix):
    executable = Path(BASE_PYTHON)
    target = Path(target_prefix).resolve()
    try:
        executable.resolve().relative_to(target)
    except ValueError:
        pass
    else:
        raise RuntimeError("An external base Python interpreter is required.")
    if not executable.is_absolute() or not executable.is_file():
        raise RuntimeError("The saved base Python interpreter is unavailable.")
    try:
        result = subprocess.run(
            [str(executable), "-I", "-c",
             "import json,sys; print(json.dumps([sys.prefix,sys.base_prefix]))"],
            check=True, capture_output=True, text=True,
        )
        prefix, base = json.loads(result.stdout)
        prefix, base = Path(prefix).resolve(), Path(base).resolve()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise RuntimeError("The saved base Python interpreter could not be validated.") from error
    if prefix != base or prefix.is_relative_to(target):
        raise RuntimeError("The saved interpreter is not an independent base Python.")
    return executable

def _inspection(directory, app_id):
    authority = directory / "installation.json"
    if directory.is_symlink() or authority.is_symlink() or not authority.is_file():
        raise RuntimeError("Saved installation authority is unavailable or unsafe.")
    raw = json.loads(authority.read_text(encoding="utf-8"))
    target = (raw.get("current") or raw.get("last_successful")) if isinstance(raw, dict) else None
    outputs = target.get("owned_outputs") if isinstance(target, dict) else None
    for name in ("inspection.py", "uninstall.py"):
        expected = next((item.get("digest") for item in outputs
                         if isinstance(item, dict) and item.get("kind") == "support"
                         and item.get("path") == name), None) if isinstance(outputs, list) else None
        path = directory / name
        if (not isinstance(expected, str) or path.is_symlink() or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise RuntimeError(f"Saved {name} differs from recorded support.")
    result = subprocess.run(
        [BASE_PYTHON, str(directory / "inspection.py"), "--directory", str(directory),
         "--app-id", app_id],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--app-id", default='buildben')
    parser.add_argument("--dry-run", action="store_true")
    args, forwarded = parser.parse_known_args()
    directory = args.directory or _installation_directory(args.app_id)
    saved = directory / "uninstall.py"
    if Path(__file__).resolve() != saved.resolve(strict=False):
        if saved.is_symlink() or not saved.is_file():
            print("Saved uninstaller is unavailable.", file=sys.stderr)
            return 2
        dispatch = [BASE_PYTHON, str(saved), "--directory", str(directory)]
        if args.dry_run:
            dispatch.append("--dry-run")
        return subprocess.run([*dispatch, *forwarded], check=False).returncode
    try:
        inspection = _inspection(directory, args.app_id)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Saved installation inspection failed: {error}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps(inspection, ensure_ascii=False, sort_keys=True))
        return 0
    record = inspection.get("record")
    target = (record.get("current") or record.get("last_successful")) if isinstance(record, dict) else None
    if not isinstance(target, dict):
        print("Saved backend identity is unavailable.", file=sys.stderr)
        return 2
    backend = target.get("backend")
    if not isinstance(backend, dict):
        print("Saved uv backend identity is unavailable.", file=sys.stderr)
        return 2
    uv = Path(backend.get("executable", ""))
    if not uv.is_absolute() or not uv.is_file():
        print("Recorded uv executable is unavailable.", file=sys.stderr)
        return 2
    outputs = target.get("owned_outputs")
    digest = next((item.get("digest") for item in outputs
                   if isinstance(item, dict) and item.get("kind") == "support"
                   and item.get("path") == "app-uninstall.py"), None) if isinstance(outputs, list) else None
    uninstall = directory / "app-uninstall.py"
    if (not isinstance(digest, str) or uninstall.is_symlink() or not uninstall.is_file()
            or hashlib.sha256(uninstall.read_bytes()).hexdigest() != digest):
        print("Saved application uninstaller differs from recorded support.", file=sys.stderr)
        return 2
    try:
        python = _base_python(target["prefix"])
    except (OSError, RuntimeError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    environment = dict(os.environ)
    environment["UV_TOOL_DIR"] = backend["tool_dir"]
    environment["UV_TOOL_BIN_DIR"] = backend["bin_dir"]
    return subprocess.run(
        [str(uv), "run", "--no-config", "--no-project", "--python", str(python),
         "--script", str(uninstall), "--directory", str(directory), *forwarded],
        env=environment, check=False,
    ).returncode

if __name__ == "__main__":
    raise SystemExit(main())
