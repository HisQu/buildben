"""Consumer and failure-boundary tests for the standalone lifecycle engine."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest

from buildben_dev.distribution import lifecycle as engine


@dataclass
class Installation:
    root: Path
    uv: Path
    original_uv: Path
    python: str
    environment: dict[str, str]
    directory: Path
    wheel: Path

    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.python, str(Path(engine.__file__).resolve()), *arguments],
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def uv_command(
        self, *arguments: str, default: bool = False
    ) -> subprocess.CompletedProcess[str]:
        environment = self.environment.copy()
        if default:
            environment.pop("UV_TOOL_DIR", None)
            environment.pop("UV_TOOL_BIN_DIR", None)
        return subprocess.run(
            [str(self.uv), *arguments],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def record(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.command(
            "record",
            "--uv",
            str(self.uv),
            "--version",
            "1.2.3",
            "--source-ref",
            "v1.2.3",
            *extra,
        )

    def install(self, wheel: Path | None = None, default: bool = False) -> None:
        result = self.uv_command(
            "tool",
            "install",
            "--offline",
            "--python",
            self.python,
            str(wheel or self.wheel),
            default=default,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def receipt(self) -> engine.Receipt:
        return engine._validate_receipt(
            json.loads((self.directory / "receipt.json").read_text(encoding="utf-8"))
        )

    def saved(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        launcher = self.directory / (
            "uninstall.cmd" if os.name == "nt" else "uninstall.sh"
        )
        command = (
            ["cmd.exe", "/d", "/c", str(launcher), *arguments]
            if os.name == "nt"
            else [str(launcher), *arguments]
        )
        return subprocess.run(
            command, env=self.environment, text=True, capture_output=True, check=False
        )


def _wheel(directory: Path, name: str) -> Path:
    """Create an installable dependency-free consumer with two entry points."""
    wheel = directory / f"{name}-1.2.3-py3-none-any.whl"
    metadata = f"{name}-1.2.3.dist-info"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"{name}.py", "def main():\n    print('installed consumer')\n")
        archive.writestr(
            f"{metadata}/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.2.3\n",
        )
        archive.writestr(
            f"{metadata}/WHEEL",
            "Wheel-Version: 1.0\nGenerator: lifecycle-tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(
            f"{metadata}/entry_points.txt",
            f"[console_scripts]\n{name} = {name}:main\n{name}-second = {name}:main\n",
        )
        archive.writestr(f"{metadata}/RECORD", "")
    return wheel


@pytest.fixture
def installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Installation]:
    """Install a tiny real tool under disposable HOME and copied uv binaries."""
    uv_source = shutil.which("uv")
    assert uv_source is not None, (
        "Lifecycle consumer tests require the existing uv runner."
    )
    # > Resolve an existing base interpreter without permitting a download.
    discovery = subprocess.run(
        [
            uv_source,
            "python",
            "find",
            "--system",
            "--no-project",
            "--no-python-downloads",
            ">=3.12",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert discovery.returncode == 0, discovery.stdout + discovery.stderr
    root = tmp_path / "isolated lifecycle with spaces"
    root.mkdir()
    directories = {
        key: root / value
        for key, value in {
            "HOME": "home",
            "USERPROFILE": "home",
            "XDG_STATE_HOME": "state",
            "LOCALAPPDATA": "local data",
            "XDG_DATA_HOME": "data",
            "XDG_CONFIG_HOME": "config",
            "XDG_CACHE_HOME": "cache",
            "UV_TOOL_DIR": "custom tools",
            "UV_TOOL_BIN_DIR": "custom tool bins",
            "UV_CACHE_DIR": "uv cache",
        }.items()
    }
    for key, directory in directories.items():
        directory.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(key, str(directory))
    binary_dir = root / "standalone bin"
    binary_dir.mkdir()
    uv = binary_dir / ("uv.exe" if os.name == "nt" else "uv")
    shutil.copy2(uv_source, uv)
    companion = binary_dir / ("uvx.exe" if os.name == "nt" else "uvx")
    shutil.copy2(uv_source, companion)
    environment = dict(os.environ)
    directory = (
        (
            directories["LOCALAPPDATA"]
            if os.name == "nt"
            else directories["XDG_STATE_HOME"]
        )
        / "buildben"
        / "installation"
    )
    fixture = Installation(
        root,
        uv,
        Path(uv_source),
        discovery.stdout.strip(),
        environment,
        directory,
        _wheel(root, "buildben"),
    )
    fixture.install()
    yield fixture


@pytest.mark.parametrize(
    ("stdout", "stderr", "code", "expected"),
    [
        ("buildben v1.2.3\n- buildben\n- bube\n", "", 0, {"buildben"}),
        ("My.Tool v2.0 (from local source)\n- first\n- second\n", "", 0, {"my-tool"}),
        ("", "No tools installed\n", 0, set()),
        ("", "", 0, set()),
    ],
)
def test_inventory_bounded_format(
    stdout: str, stderr: str, code: int, expected: set[str]
) -> None:
    assert engine.parse_inventory(stdout, stderr, code) == expected


@pytest.mark.parametrize(
    ("stdout", "stderr", "code"),
    [
        ("- orphan\n", "", 0),
        ("buildben v1\nbuildben v2\n", "", 0),
        ("buildben v1\nunknown\n", "", 0),
        ("", "unexpected warning", 0),
        ("", "", 1),
    ],
)
def test_inventory_unknown_is_not_empty(stdout: str, stderr: str, code: int) -> None:
    with pytest.raises(engine.LifecycleError):
        engine.parse_inventory(stdout, stderr, code)


def test_real_inventory_default_uninstall_and_actual_saved_launcher(
    installation: Installation,
) -> None:
    listing = installation.uv_command(
        "tool", "list", "--color", "never", "--offline", "--no-config"
    )
    assert engine.parse_inventory(
        listing.stdout, listing.stderr, listing.returncode
    ) == {"buildben"}
    for name in ("buildben", "buildben-second"):
        executable = Path(installation.environment["UV_TOOL_BIN_DIR"]) / (
            name + (".exe" if os.name == "nt" else "")
        )
        invocation = subprocess.run(
            [str(executable)],
            env=installation.environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert invocation.returncode == 0, invocation.stdout + invocation.stderr
        assert invocation.stdout.strip() == "installed consumer"
    assert installation.record("--uv-bootstrapped", "--check").returncode == 0
    assert not installation.directory.exists()
    result = installation.record("--uv-bootstrapped")
    assert result.returncode == 0, result.stdout + result.stderr
    sentinel = installation.root / "data" / "payload"
    sentinel.write_text("keep", encoding="utf-8")
    installation.environment["UV_TOOL_DIR"] = str(
        installation.root / "misleading tools"
    )
    installation.environment["UV_TOOL_BIN_DIR"] = str(
        installation.root / "misleading bins"
    )
    removed = installation.saved("--yes")
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert installation.receipt()["package_removed"]
    assert installation.uv.is_file()
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert installation.saved("--yes").returncode == 0


def test_real_owned_uv_removal_missing_uv_repeat_and_reinstall(
    installation: Installation,
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    receipt = installation.receipt()
    assert receipt["uv_bootstrapped"]
    expected = {"uv.exe", "uvx.exe"} if os.name == "nt" else {"uv", "uvx"}
    assert {Path(item["path"]).name for item in receipt["uv_binaries"]} == expected
    sentinels = [
        installation.root / "cache" / "keep",
        installation.root / "home" / ".profile",
    ]
    for sentinel in sentinels:
        sentinel.write_text("keep", encoding="utf-8")
    removed = installation.saved("--yes", "--remove-uv")
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not installation.uv.exists()
    assert installation.original_uv.is_file()
    before = (installation.directory / "receipt.json").read_bytes()
    assert installation.saved("--yes").returncode == 0
    assert installation.saved("--yes", "--clean-appdata").returncode != 0
    assert (installation.directory / "receipt.json").read_bytes() == before
    assert all(path.read_text(encoding="utf-8") == "keep" for path in sentinels)
    shutil.copy2(installation.original_uv, installation.uv)
    installation.install()
    refreshed = installation.record()
    assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
    assert installation.receipt()["package_removed"] is False


@pytest.mark.parametrize("other_default", [False, True])
def test_second_real_tool_prevents_uv_removal_before_package_mutation(
    installation: Installation, other_default: bool
) -> None:
    installation.install(
        _wheel(installation.root, "another_tool"), default=other_default
    )
    assert installation.record("--uv-bootstrapped").returncode == 0
    result = installation.saved("--yes", "--remove-uv")
    assert result.returncode != 0
    assert installation.uv.is_file()
    assert installation.receipt()["package_removed"] is False
    assert (
        "buildben"
        in installation.uv_command(
            "tool", "list", "--color", "never", "--offline", "--no-config"
        ).stdout
    )


@pytest.mark.parametrize("ownership", ["unowned", "changed", "linked"])
def test_uv_identity_ineligibility_preserves_package(
    installation: Installation, ownership: str
) -> None:
    assert (
        installation.record(
            *([] if ownership == "unowned" else ["--uv-bootstrapped"])
        ).returncode
        == 0
    )
    companion = installation.uv.with_name("uvx.exe" if os.name == "nt" else "uvx")
    if ownership == "changed":
        companion.write_bytes(b"different binary")
    elif ownership == "linked":
        companion.unlink()
        try:
            companion.symlink_to(installation.uv)
        except OSError:
            pytest.skip("Creating symlinks is not permitted on this runner.")
    result = installation.saved("--yes", "--remove-uv")
    assert result.returncode != 0
    assert installation.receipt()["package_removed"] is False
    # > Ineligibility must not block package-only removal.
    ordinary = installation.saved("--yes")
    assert ordinary.returncode == 0, ordinary.stdout + ordinary.stderr
    assert installation.uv.is_file()


@pytest.mark.parametrize("malformed", [False, True])
def test_explicit_legacy_package_only_recovery(
    installation: Installation, malformed: bool
) -> None:
    if malformed:
        installation.directory.mkdir(parents=True)
        (installation.directory / "receipt.json").write_text(
            "not-json", encoding="utf-8"
        )
    assert installation.command("--yes").returncode != 0
    assert (
        installation.command(
            "--yes", "--uv", str(installation.uv), "--remove-uv"
        ).returncode
        != 0
    )
    removed = installation.command("--yes", "--uv", str(installation.uv))
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert installation.uv.is_file()
    if malformed:
        assert (installation.directory / "receipt.json").read_text(
            encoding="utf-8"
        ) == "not-json"


def test_stale_completion_marker_does_not_remove_new_installation(
    installation: Installation,
) -> None:
    assert installation.record().returncode == 0
    receipt_path = installation.directory / "receipt.json"
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    data["package_removed"] = True
    receipt_path.write_text(json.dumps(data), encoding="utf-8")
    result = installation.saved("--yes")
    assert result.returncode != 0
    assert "rerun the installer" in result.stderr


@pytest.mark.parametrize("occupied", ["lifecycle.py", "uninstall.sh", "unknown"])
def test_occupied_state_without_receipt_is_not_overwritten(
    installation: Installation, occupied: str
) -> None:
    installation.directory.mkdir(parents=True)
    target = installation.directory / occupied
    target.write_text("unrecognized", encoding="utf-8")
    result = installation.record("--check")
    assert result.returncode != 0
    assert target.read_text(encoding="utf-8") == "unrecognized"
    assert not (installation.directory / "receipt.json").exists()


def test_conflicting_layout_rejected_during_check(installation: Installation) -> None:
    assert installation.record().returncode == 0
    before = (installation.directory / "receipt.json").read_bytes()
    installation.environment["UV_TOOL_DIR"] = str(installation.root / "different tools")
    assert installation.record("--check").returncode != 0
    assert (installation.directory / "receipt.json").read_bytes() == before


def test_linked_support_rejected_before_recording(installation: Installation) -> None:
    assert installation.record().returncode == 0
    helper = installation.directory / "lifecycle.py"
    helper.unlink()
    try:
        helper.symlink_to(installation.root / "not-owned")
    except OSError:
        pytest.skip("Creating symlinks is not permitted on this runner.")
    assert installation.record("--check").returncode != 0


def test_atomic_marker_failure_preserves_previous_receipt(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert installation.record().returncode == 0
    receipt = installation.receipt()
    original = (installation.directory / "receipt.json").read_bytes()

    def interrupted(source: str, destination: Path) -> None:
        raise OSError("interrupted replacement")

    monkeypatch.setattr(engine.os, "replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        engine._receipt_update(receipt, package_removed=True)
    assert (installation.directory / "receipt.json").read_bytes() == original
    assert receipt["package_removed"] is False


def test_marker_failure_keeps_uv_after_real_package_removal(
    installation: Installation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0

    def fail_save(receipt: engine.Receipt, *, package_removed: bool) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(engine, "_receipt_update", fail_save)
    result = engine.main(["--yes", "--remove-uv"])
    assert result != 0
    assert installation.uv.is_file()
    assert "tool uninstall buildben" in capsys.readouterr().err


def test_companion_unlink_failure_retains_uv(
    installation: Installation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    original_unlink = Path.unlink
    companion = installation.uv.with_name("uvx.exe" if os.name == "nt" else "uvx")

    def deny_companion(path: Path, missing_ok: bool = False) -> None:
        if path == companion:
            raise PermissionError("binary is in use")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", deny_companion)
    assert engine.main(["--yes", "--remove-uv"]) != 0
    assert installation.uv.is_file()
    assert "incomplete" in capsys.readouterr().err


def test_unknown_inventory_aborts_before_uninstall(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert installation.record().returncode == 0
    original = engine._run

    def unknown(
        argv: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["tool", "list"]:
            return subprocess.CompletedProcess(argv, 0, "unexpected output", "")
        return original(argv, env=env)

    monkeypatch.setattr(engine, "_run", unknown)
    assert engine.main(["--yes"]) != 0
    assert installation.receipt()["package_removed"] is False


@pytest.mark.parametrize(
    "field", ["schema_version", "appdata_supported", "uv_binaries"]
)
def test_receipt_strict_schema_rejects_unsafe_identity(
    installation: Installation, field: str
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    data = dict(installation.receipt())
    if field == "schema_version":
        data[field] = True
    elif field == "appdata_supported":
        data[field] = True
    else:
        binaries = installation.receipt()["uv_binaries"]
        data[field] = [*binaries, *binaries]
    with pytest.raises(engine.LifecycleError):
        engine._validate_receipt(data)


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("failure", ["overlap", "preview", "child", "malformed"])
def test_cleanup_failure_leaves_real_package_installed(
    installation: Installation,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    dry_run: bool,
) -> None:
    assert installation.record().returncode == 0
    monkeypatch.setattr(engine, "APPDATA_SUPPORTED", True)
    receipt_path = installation.directory / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["appdata_supported"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    inventory = {
        "apprc_dir": str(installation.root / "appdata"),
        "managed_files": [],
        "internal_storage_roots": [str(installation.directory.parent)]
        if failure == "overlap"
        else [],
        "external_storage_roots": [],
        "stale_storage": False,
        "stale_user_dotenv": False,
    }
    original_run = engine._run
    original_subprocess = subprocess.run

    def appdata(
        argv: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        if "appdata" not in argv:
            return original_run(argv, env=env)
        if "paths" in argv:
            return subprocess.CompletedProcess(
                argv,
                0,
                "not-json" if failure == "malformed" else json.dumps(inventory),
                "",
            )
        return subprocess.CompletedProcess(
            argv, 1 if failure == "preview" else 0, "", "cleanup failed"
        )

    def child(
        argv: list[str],
        *,
        env: dict[str, str] | None = None,
        check: bool = False,
        text: bool = True,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if "appdata" in argv and "clean" in argv and "--dry-run" not in argv:
            return subprocess.CompletedProcess(argv, 1, "", "")
        return original_subprocess(
            argv, env=env, check=check, text=True, capture_output=capture_output
        )

    monkeypatch.setattr(engine, "_run", appdata)
    if failure == "child":
        monkeypatch.setattr(engine.subprocess, "run", child)
    before = receipt_path.read_bytes()
    arguments = (
        ["--dry-run", "--clean-appdata"] if dry_run else ["--yes", "--clean-appdata"]
    )
    result = engine.main(arguments)
    if dry_run and failure == "child":
        assert result == 0
    else:
        assert result != 0
    assert receipt_path.read_bytes() == before
    assert installation.receipt()["package_removed"] is False
    listing = installation.uv_command(
        "tool", "list", "--color", "never", "--offline", "--no-config"
    )
    assert "buildben" in listing.stdout


def test_failed_package_uninstall_never_marks_completion(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    original = engine._run

    def fail_uninstall(
        argv: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["tool", "uninstall"]:
            return subprocess.CompletedProcess(argv, 9, "", "intentional failure")
        return original(argv, env=env)

    monkeypatch.setattr(engine, "_run", fail_uninstall)
    assert engine.main(["--yes", "--remove-uv"]) != 0
    assert installation.receipt()["package_removed"] is False
    assert installation.uv.is_file()


def test_interactive_uv_default_no_retains_owned_binaries(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    answers = iter(["y", ""])
    monkeypatch.setattr(engine.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    assert engine.main([]) == 0
    assert installation.uv.is_file()
    assert installation.receipt()["package_removed"] is True


def test_dry_run_never_rewrites_receipt(installation: Installation) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    before = (installation.directory / "receipt.json").read_bytes()
    result = installation.saved("--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (installation.directory / "receipt.json").read_bytes() == before
    assert installation.receipt()["package_removed"] is False


def test_new_companion_during_uninstall_prevents_uv_deletion(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    companion = installation.uv.with_name("uvx.exe" if os.name == "nt" else "uvx")
    companion.unlink()
    assert installation.record("--uv-bootstrapped").returncode == 0
    original = engine._run

    def introduce_companion(
        argv: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        result = original(argv, env=env)
        if argv[1:3] == ["tool", "uninstall"] and result.returncode == 0:
            shutil.copy2(installation.original_uv, companion)
        return result

    monkeypatch.setattr(engine, "_run", introduce_companion)
    assert engine.main(["--yes", "--remove-uv"]) != 0
    assert installation.uv.is_file()
    assert installation.receipt()["package_removed"] is True


def test_source_native_recovery_uses_existing_base_python(
    installation: Installation,
) -> None:
    distribution = Path(engine.__file__).parent
    if os.name == "nt":
        command = [
            "cmd.exe",
            "/d",
            "/c",
            str(distribution / "uninstall.cmd"),
            "--yes",
            "--uv",
            str(installation.uv),
        ]
    else:
        command = [
            str(distribution / "uninstall.sh"),
            "--yes",
            "--uv",
            str(installation.uv),
        ]
    result = subprocess.run(
        command,
        env=installation.environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not installation.directory.exists()
    assert installation.uv.is_file()


@pytest.mark.parametrize(
    "metadata",
    [
        "null",
        "[]",
        "[1, 1, [3, 12]]",
        '["base", "base", ["3", 12]]',
        '["venv", "base", [3, 12]]',
    ],
)
def test_invalid_recorded_interpreter_metadata_fails_closed(
    installation: Installation, monkeypatch: pytest.MonkeyPatch, metadata: str
) -> None:
    assert installation.record().returncode == 0
    original = engine._run

    def invalid(
        argv: list[str], *, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        if "-c" in argv:
            return subprocess.CompletedProcess(argv, 0, metadata, "")
        return original(argv, env=env)

    monkeypatch.setattr(engine, "_run", invalid)
    assert engine.main(["--yes"]) != 0
    assert installation.receipt()["package_removed"] is False


def test_missing_native_preflight_is_rejected_during_check(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        engine, "__file__", str(installation.root / "archive" / "lifecycle.py")
    )
    assert (
        engine.main(
            [
                "record",
                "--uv",
                str(installation.uv),
                "--version",
                "1.2.3",
                "--source-ref",
                "v1.2.3",
                "--check",
            ]
        )
        != 0
    )
    assert not installation.directory.exists()


def test_relative_platform_state_root_is_rejected(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_STATE_HOME", "relative-state"
    )
    with pytest.raises(engine.LifecycleError, match="absolute"):
        engine.state_dir()


def test_state_cannot_live_under_removable_tools(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = str(Path(installation.environment["UV_TOOL_DIR"]) / "private state")
    monkeypatch.setenv("LOCALAPPDATA" if os.name == "nt" else "XDG_STATE_HOME", root)
    assert (
        engine.main(
            [
                "record",
                "--uv",
                str(installation.uv),
                "--version",
                "1.2.3",
                "--source-ref",
                "v1.2.3",
                "--check",
            ]
        )
        != 0
    )
    assert not Path(root).exists()


def test_completed_appdata_receipt_rejects_cleanup_without_uv(
    installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    result = installation.saved("--yes", "--remove-uv")
    assert result.returncode == 0, result.stdout + result.stderr
    monkeypatch.setattr(engine, "APPDATA_SUPPORTED", True)
    receipt_path = installation.directory / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["appdata_supported"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    before = receipt_path.read_bytes()
    assert engine.main(["--yes", "--clean-appdata"]) != 0
    assert receipt_path.read_bytes() == before
    assert not installation.uv.exists()


@pytest.mark.parametrize("uv_answer", ["", "y"])
def test_explicit_remove_uv_requires_separate_interactive_consent(
    installation: Installation, monkeypatch: pytest.MonkeyPatch, uv_answer: str
) -> None:
    assert installation.record("--uv-bootstrapped").returncode == 0
    answers = iter(["y", uv_answer])
    monkeypatch.setattr(engine.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    assert engine.main(["--remove-uv"]) == 0
    assert installation.receipt()["package_removed"] is True
    assert installation.uv.exists() is (uv_answer != "y")
    companion = installation.uv.with_name("uvx.exe" if os.name == "nt" else "uvx")
    assert companion.exists() is (uv_answer != "y")


@pytest.mark.skipif(
    os.name != "nt", reason="CMD/PowerShell native staging requires Windows."
)
def test_staged_source_powershell_keeps_original_helper_path(
    installation: Installation,
) -> None:
    source = installation.root / "native source with spaces"
    staged = source / "temporary staging"
    staged.mkdir(parents=True)
    distribution = Path(engine.__file__).parent
    for name in ("uninstall.cmd", "uninstall.ps1", "lifecycle.py"):
        shutil.copy2(distribution / name, source / name)
    # > Reproduce the existing preflight's PS-only staging result without changing policy.
    (source / "prepare-powershell-windows.cmd").write_text(
        "@echo off\n"
        'copy /b "%~1" "%~dp0temporary staging\\uninstall.ps1" >nul\n'
        "if errorlevel 1 exit /b 1\n"
        'set "BUILDBEN_PREPARED_SCRIPT=%~dp0temporary staging\\uninstall.ps1"\n'
        'set "BUILDBEN_STAGED_SCRIPT=%~dp0temporary staging\\uninstall.ps1"\n'
        "exit /b 0\n",
        encoding="utf-8",
    )
    assert not (staged / "lifecycle.py").exists()
    result = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            str(source / "uninstall.cmd"),
            "--yes",
            "--uv",
            str(installation.uv),
        ],
        env=installation.environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    listing = installation.uv_command(
        "tool", "list", "--color", "never", "--offline", "--no-config"
    )
    assert (
        engine.parse_inventory(listing.stdout, listing.stderr, listing.returncode)
        == set()
    )
    assert installation.uv.is_file()
    assert not installation.directory.exists()
