#!/usr/bin/env python3
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--app-id", default='buildben')
    parser.add_argument("--command", default='bube')
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    directory = args.directory or _installation_directory(args.app_id)
    saved = directory / "launcher.py"
    if Path(__file__).resolve() != saved.resolve(strict=False):
        if saved.is_symlink() or not saved.is_file():
            print("Saved launcher is unavailable; repair the installation.", file=sys.stderr)
            return 2
        return subprocess.run(
            [sys.executable, str(saved), "--directory", str(directory),
             "--command", args.command, *args.arguments],
            check=False,
        ).returncode
    try:
        record = json.loads((directory / "installation.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"Installation metadata is unavailable: {error}", file=sys.stderr)
        return 2
    current = record.get("current")
    identity = current.get("identity") if isinstance(current, dict) else None
    commands = identity.get("commands") if isinstance(identity, dict) else None
    entries = current.get("commands") if isinstance(current, dict) else None
    outputs = current.get("owned_outputs") if isinstance(current, dict) else None
    if record.get("status") != "ready" or record.get("operation") is not None:
        print("Application is not installed; use the saved installer to repair it.", file=sys.stderr)
        return 2
    if not isinstance(outputs, list):
        print("Saved launcher ownership is unavailable.", file=sys.stderr)
        return 2
    digest = next((item.get("digest") for item in outputs
                   if isinstance(item, dict) and item.get("kind") == "support"
                   and item.get("path") == "launcher.py"), None)
    if not isinstance(digest, str) or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != digest:
        print("Saved launcher differs from recorded support.", file=sys.stderr)
        return 2
    if not isinstance(commands, list) or not isinstance(entries, list) or args.command not in commands:
        print("Recorded application command is unavailable.", file=sys.stderr)
        return 2
    executable = Path(entries[commands.index(args.command)])
    if not executable.is_absolute() or not executable.is_file():
        print("Recorded application command is missing; repair the installation.", file=sys.stderr)
        return 2
    return subprocess.run([str(executable), *args.arguments], check=False).returncode

if __name__ == "__main__":
    raise SystemExit(main())
