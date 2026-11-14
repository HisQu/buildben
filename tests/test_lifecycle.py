"""Real generated-consumer editable lifecycle and authority safety tests."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from support_native_release import pin_fixture_sdk, sdk_authoring_environment


@dataclass(frozen=True, slots=True)
class Consumer:
    """Keep a real scaffold and its isolated developer-owned environment together."""

    root: Path
    environment: dict[str, str]
    directory: Path
    uv: Path
    name: str = "lifecycle_consumer"

    @property
    def command(self) -> Path:
        """Return the checkout's installed console entry point."""
        return (
            self.root
            / ".venv"
            / ("Scripts" if os.name == "nt" else "bin")
            / (self.name + (".exe" if os.name == "nt" else ""))
        )

    @property
    def global_command(self) -> Path:
        """Return the independently registered command."""
        return Path(self.environment["UV_TOOL_BIN_DIR"]) / self.command.name

    def run(
        self, *arguments: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Invoke the actual app entry point without shell dispatch."""
        return subprocess.run(
            [str(self.command), *arguments],
            cwd=cwd or self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def register(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Exercise the documented uv-run editable registration path."""
        return subprocess.run(
            [
                str(self.uv),
                "run",
                "--locked",
                self.name,
                "app",
                "install",
                "-e",
                "--yes",
                "--skip-setup",
                *arguments,
            ],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def record(self) -> dict[str, Any]:
        """Read the actual persisted installation authority."""
        return json.loads(
            (self.directory / "installation.json").read_text(encoding="utf-8")
        )


def _succeeded(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def consumer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Consumer:
    """Sync one real scaffold before AppRC registers its existing environment.

    :param tmp_path: Isolated checkout, resource and command roots.
    :param monkeypatch: Suppress only the scaffolder's overwrite prompt.
    :return: Consumer whose environment is owned by uv, never by AppRC.
    """
    from apprc.user_files.installation.discovery import installation_directory

    import buildben.init_proj as scaffolder

    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("The maintained editable consumer smoke requires uv.")
    monkeypatch.setattr(scaffolder.utils, "warn_dir_overwrite", lambda _path: None)
    destination = tmp_path / "consumer space"
    destination.mkdir()
    scaffolder._run(
        argparse.Namespace(
            name="lifecycle_consumer",
            target_dir=str(destination),
            git_init=False,
            github_user="fixture-owner",
            frontend=None,
        )
    )
    root = destination / "lifecycle_consumer"
    environment, revision, _ = sdk_authoring_environment(root)
    pin_fixture_sdk(root, revision)
    for key in (
        "VIRTUAL_ENV",
        "PYTHONPATH",
        "PYTHONHOME",
        "UV_ACTIVE",
        "UV_PROJECT_ENVIRONMENT",
        "UV_NO_SYNC",
    ):
        environment.pop(key, None)
    for key, folder in {
        "HOME": "home",
        "USERPROFILE": "home",
        "XDG_STATE_HOME": "state",
        "XDG_DATA_HOME": "data",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "LOCALAPPDATA": "local data",
        "UV_TOOL_BIN_DIR": "command directory",
    }.items():
        path = tmp_path / folder
        path.mkdir(exist_ok=True)
        environment[key] = str(path)
    environment["PATH"] = os.pathsep.join(
        (environment["UV_TOOL_BIN_DIR"], environment.get("PATH", ""))
    )
    environment["UV"] = str(Path(uv).resolve())
    environment["UV_PYTHON_DOWNLOADS"] = "never"
    for arguments in (
        ("lock", "--python", sys.executable),
        ("sync", "--locked", "--no-default-groups", "--python", sys.executable),
    ):
        result = subprocess.run(
            [str(uv), *arguments],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        _succeeded(result)
    # > Registration must reuse this already synchronized environment.
    environment["UV_NO_SYNC"] = "1"
    (root / "checkout-sentinel.txt").write_bytes(b"developer checkout\n")
    (root / ".venv" / "environment-sentinel.txt").write_bytes(
        b"developer environment\n"
    )
    return Consumer(
        root,
        environment,
        installation_directory("lifecycle_consumer", environment=environment),
        Path(uv).resolve(),
    )


def _assert_checkout_retained(consumer: Consumer) -> None:
    assert (consumer.root / "checkout-sentinel.txt").read_bytes() == (
        b"developer checkout\n"
    )
    assert (
        consumer.root / ".venv" / "environment-sentinel.txt"
    ).read_bytes() == b"developer environment\n"
    assert consumer.command.is_file()


def test_editable_registration_reuses_environment_and_live_source(
    consumer: Consumer, tmp_path: Path
) -> None:
    """Register a checkout, run elsewhere and observe later source edits."""
    environment = consumer.root / ".venv"
    before = environment.stat()
    configuration = (environment / "pyvenv.cfg").read_bytes()
    lock = (consumer.root / "uv.lock").read_bytes()
    _succeeded(consumer.register())
    record = consumer.record()
    assert record["schema_version"] == 3
    assert record["status"] == "ready"
    assert record["identity"]["app_id"] == consumer.name
    runtime = record["active_runtime"]
    assert Path(runtime["project"]) == consumer.root.resolve()
    assert Path(runtime["environment"]) == environment.resolve()
    assert record["retiring_runtime_ids"] == []
    assert (environment.stat().st_dev, environment.stat().st_ino) == (
        before.st_dev,
        before.st_ino,
    )
    assert (environment / "pyvenv.cfg").read_bytes() == configuration
    assert (consumer.root / "uv.lock").read_bytes() == lock
    _assert_checkout_retained(consumer)

    unrelated = tmp_path / "unrelated caller"
    unrelated.mkdir()
    conflicting = tmp_path / "unrelated environment"
    conflicting.mkdir()
    hostile = consumer.environment | {
        "VIRTUAL_ENV": str(conflicting),
        "PYTHONPATH": str(conflicting),
    }
    observed = subprocess.run(
        [str(consumer.global_command), "diagnose", "--json"],
        cwd=unrelated,
        env=hostile,
        capture_output=True,
        text=True,
        check=False,
    )
    _succeeded(observed)
    payload = json.loads(observed.stdout)
    assert Path(payload["package_file"]).is_relative_to(consumer.root)
    assert Path(payload["python_executable"]).parent == consumer.command.parent
    paths = consumer.run("app", "paths", "--json")
    _succeeded(paths)
    path_result = json.loads(paths.stdout)
    placement = record["placement"]
    assert path_result["layout"] == "native"
    assert path_result["source"] == "installation"
    assert path_result["paths"]["config"] == placement["config_dir"]
    assert path_result["paths"]["appdata"] == placement["appdata_dir"]

    source = consumer.root / "src" / consumer.name / "cli" / "app.py"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "typer.echo(_package_version())",
            'typer.echo("live editable source")',
            1,
        ),
        encoding="utf-8",
    )
    changed = subprocess.run(
        [str(consumer.global_command), "version"],
        cwd=unrelated,
        env=hostile,
        capture_output=True,
        text=True,
        check=False,
    )
    _succeeded(changed)
    assert changed.stdout.strip() == "live editable source"
    _succeeded(consumer.register())
    refreshed = consumer.record()
    assert refreshed["generation_id"] == record["generation_id"]
    assert refreshed["placement"] == record["placement"]
    assert refreshed["active_runtime"] == runtime
    _assert_checkout_retained(consumer)


def test_managed_install_from_checkout_requires_setup(consumer: Consumer) -> None:
    """An app without an authored installer must not invent managed acquisition."""
    refused = consumer.run("app", "install", "--yes", "--skip-setup")
    assert refused.returncode != 0
    assert "setup" in (refused.stdout + refused.stderr).lower()
    assert not (consumer.directory / "installation.json").exists()
    _assert_checkout_retained(consumer)


def test_editable_repair_leaves_environment_management_to_uv(
    consumer: Consumer,
) -> None:
    """Report the developer's recovery command without preparing a runtime slot."""
    _succeeded(consumer.register())
    before = consumer.record()
    configuration = (consumer.root / ".venv" / "pyvenv.cfg").read_bytes()
    repaired = consumer.run("app", "repair")
    assert "uv sync --locked" in repaired.stdout + repaired.stderr
    assert consumer.record() == before
    assert (consumer.root / ".venv" / "pyvenv.cfg").read_bytes() == configuration
    _assert_checkout_retained(consumer)


def test_editable_uninstall_retains_checkout_environment_and_user_data(
    consumer: Consumer, tmp_path: Path
) -> None:
    """Remove only owned integrations, then reconnect retained resource placement."""
    _succeeded(consumer.register())
    record = consumer.record()
    appdata = Path(record["placement"]["appdata_dir"])
    data = appdata / "user-data.txt"
    data.write_bytes(b"retain application data\n")
    unknown = consumer.directory / "unknown-user-file"
    unknown.write_bytes(b"do not sweep installation children\n")
    unrelated = Path(consumer.environment["UV_TOOL_BIN_DIR"]) / "unrelated-command"
    unrelated.write_bytes(b"not an AppRC integration\n")
    removed = consumer.run("app", "uninstall", "--yes", cwd=tmp_path)
    _succeeded(removed)
    retained = consumer.record()
    assert retained["status"] == "removed-retained"
    assert retained["active_runtime"] is None
    assert retained["operation"] is None
    assert not os.path.lexists(consumer.global_command)
    assert data.read_bytes() == b"retain application data\n"
    assert unknown.read_bytes() == b"do not sweep installation children\n"
    assert unrelated.read_bytes() == b"not an AppRC integration\n"
    _assert_checkout_retained(consumer)
    _succeeded(consumer.register())
    assert consumer.record()["placement"] == record["placement"]
    shown = consumer.run("config", "show", "--json")
    _succeeded(shown)


def test_installed_consumer_hooks_initialize_and_purge_exact_owned_data(
    consumer: Consumer, tmp_path: Path
) -> None:
    """Run installed providers before removing integrations, never the developer env."""
    module = consumer.root / "src" / consumer.name / "installation.py"
    module.write_text(
        textwrap.dedent('''\
            """Consumer-owned idempotent initialization and exact cleanup."""
            import os
            import sys
            from pathlib import Path

            import apprc as rc
            from apprc.definition.installation import CleanupInventory, InventoryEntry
            from apprc.distribution.runtime.controllers import default_cleanup_inventory
            from apprc.user_files.app_home.writes import file_revision

            def initialize(context):
                root = context.placement.appdata_dir
                assert root is not None
                marker = root / "consumer-owned.txt"
                if not marker.exists():
                    marker.write_bytes(b"initialized by installed provider")

            def inventory(inspection, categories, forget_retained):
                base = default_cleanup_inventory(
                    inspection, categories=categories, forget_retained=True
                )
                entries, retained = list(base.entries), list(base.retained)
                root = inspection.record.placement.appdata_dir
                if "appdata" in categories and root is not None:
                    marker = root / "consumer-owned.txt"
                    entries.append(
                        InventoryEntry(marker, "file", file_revision(marker), "appdata")
                    )
                    unknown = set(root.iterdir()) - {
                        marker, root / ".apprc-owner.json"
                    }
                    if unknown and not forget_retained:
                        raise rc.InstallationError("Unknown appdata is not owned.")
                    if not unknown:
                        retained = [item for item in retained if item.path != root]
                        entries.append(InventoryEntry(root, "directory", None, "appdata"))
                return CleanupInventory(tuple(entries), tuple(retained))

            def cleanup(context):
                sentinel = Path(os.environ["LIFECYCLE_ENV_SENTINEL"])
                assert sentinel.read_bytes() == b"developer environment\\n"
                Path(os.environ["LIFECYCLE_HOOK_LOG"]).write_text(
                    str(Path(sys.prefix)) + "\\n" + str(context.directory),
                    encoding="utf-8",
                )

            INSTALLATION_HOOKS = rc.InstallationHooks(
                initialize="lifecycle_consumer.installation:initialize",
                inventory="lifecycle_consumer.installation:inventory",
                cleanup="lifecycle_consumer.installation:cleanup",
            )
            '''),
        encoding="utf-8",
    )
    project = consumer.root / "pyproject.toml"
    with project.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n[tool.apprc.distribution.hooks]\n"
            'initialize = "lifecycle_consumer.installation:initialize"\n'
            'inventory = "lifecycle_consumer.installation:inventory"\n'
            'cleanup = "lifecycle_consumer.installation:cleanup"\n'
        )
    log = tmp_path / "provider-cleanup.log"
    consumer.environment["LIFECYCLE_HOOK_LOG"] = str(log)
    consumer.environment["LIFECYCLE_ENV_SENTINEL"] = str(
        consumer.root / ".venv" / "environment-sentinel.txt"
    )
    _succeeded(consumer.register())
    record = consumer.record()
    marker = Path(record["placement"]["appdata_dir"]) / "consumer-owned.txt"
    assert marker.read_bytes() == b"initialized by installed provider"
    marker.write_bytes(b"preserve later application changes")
    _succeeded(consumer.register())
    assert marker.read_bytes() == b"preserve later application changes"
    removed = consumer.run(
        "app",
        "uninstall",
        "--complete",
        "--category",
        "config",
        "--category",
        "appdata",
        "--yes",
    )
    _succeeded(removed)
    assert log.read_text(encoding="utf-8").splitlines() == [
        str((consumer.root / ".venv").resolve()),
        str(consumer.directory),
    ]
    assert not marker.exists()
    assert not os.path.lexists(consumer.global_command)
    _assert_checkout_retained(consumer)


def test_editable_registration_refuses_unknown_command_collision(
    consumer: Consumer,
) -> None:
    consumer.global_command.write_bytes(b"unowned command\n")
    refused = consumer.register()
    assert refused.returncode != 0
    assert consumer.global_command.read_bytes() == b"unowned command\n"
    assert not (consumer.directory / "installation.json").exists()
    assert not (Path(consumer.environment["XDG_CONFIG_HOME"]) / consumer.name).exists()
    assert not (
        Path(consumer.environment["XDG_DATA_HOME"]) / consumer.name / "appdata"
    ).exists()
    _assert_checkout_retained(consumer)


@pytest.mark.parametrize("location", ["off-path", "checkout", "environment"])
def test_registration_requires_external_command_directory_on_path(
    consumer: Consumer, tmp_path: Path, location: str
) -> None:
    """Do not claim a developer-owned directory or invent PATH/profile changes."""
    directory = {
        "off-path": tmp_path / "not-on-path",
        "checkout": consumer.root / "global-commands",
        "environment": consumer.root / ".venv" / "global-commands",
    }[location]
    directory.mkdir()
    if location != "off-path":
        consumer.environment["PATH"] = os.pathsep.join(
            (str(directory), consumer.environment["PATH"])
        )
    refused = consumer.register("--command-directory", str(directory))
    assert refused.returncode != 0
    assert not tuple(directory.iterdir())
    assert not (consumer.directory / "installation.json").exists()
    _assert_checkout_retained(consumer)


def test_registration_rejects_an_interpreter_outside_checkout_environment(
    consumer: Consumer,
) -> None:
    """A source import cannot substitute the active repository's actual venv."""
    venv_config = (consumer.root / ".venv" / "pyvenv.cfg").read_bytes()
    environment_sentinel = (
        consumer.root / ".venv" / "environment-sentinel.txt"
    ).read_bytes()
    refused = subprocess.run(
        [
            sys.executable,
            "-m",
            consumer.name,
            "app",
            "install",
            "-e",
            "--yes",
            "--skip-setup",
        ],
        cwd=consumer.root,
        env=consumer.environment | {"PYTHONPATH": str(consumer.root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode != 0
    assert not (consumer.directory / "installation.json").exists()
    assert not os.path.lexists(consumer.global_command)
    assert (consumer.root / ".venv" / "pyvenv.cfg").read_bytes() == venv_config
    assert (
        consumer.root / ".venv" / "environment-sentinel.txt"
    ).read_bytes() == environment_sentinel
    _assert_checkout_retained(consumer)


@pytest.mark.skipif(os.name == "nt", reason="POSIX readlink ownership.")
def test_retargeted_command_link_is_not_deleted(
    consumer: Consumer, tmp_path: Path
) -> None:
    """Identical destination bytes do not authorize deleting a different link."""
    _succeeded(consumer.register())
    command = consumer.global_command
    assert command.is_symlink()
    original = os.readlink(command)
    replacement = tmp_path / "unowned command target"
    replacement.write_bytes(consumer.command.read_bytes())
    command.unlink()
    command.symlink_to(replacement)
    before = consumer.record()
    removed = consumer.run("app", "uninstall", "--yes")
    assert "Refusing to remove a modified global command" in (
        removed.stdout + removed.stderr
    )
    updated = consumer.record()
    assert updated["operation"] is not None
    assert updated["operation"] != before["operation"]
    assert command.is_symlink()
    assert os.readlink(command) == str(replacement)
    assert replacement.read_bytes() == consumer.command.read_bytes()
    _assert_checkout_retained(consumer)
    command.unlink()
    command.symlink_to(original)
    _succeeded(consumer.run("app", "uninstall", "--yes"))
    assert not os.path.lexists(command)


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent symlink containment.")
@pytest.mark.parametrize("boundary", ["installation", "command-directory"])
def test_registration_rejects_linked_lifecycle_boundaries(
    consumer: Consumer, tmp_path: Path, boundary: str
) -> None:
    """Do not canonicalize user-selected lifecycle paths to bypass link guards."""
    outside = tmp_path / "outside lifecycle boundary"
    outside.mkdir()
    sentinel = outside / "unowned"
    sentinel.write_bytes(b"preserve linked target\n")
    if boundary == "installation":
        consumer.directory.parent.mkdir(parents=True, exist_ok=True)
        consumer.directory.symlink_to(outside, target_is_directory=True)
        arguments: tuple[str, ...] = ()
    else:
        linked = tmp_path / "linked command directory"
        linked.symlink_to(outside, target_is_directory=True)
        consumer.environment["PATH"] = os.pathsep.join(
            (str(linked), consumer.environment["PATH"])
        )
        arguments = ("--command-directory", str(linked))
    refused = consumer.register(*arguments)
    assert refused.returncode != 0
    assert sentinel.read_bytes() == b"preserve linked target\n"
    assert not (outside / "installation.json").exists()
    assert not (outside / consumer.command.name).exists()
    _assert_checkout_retained(consumer)


@pytest.mark.parametrize("invalid", ["{invalid", '{"schema_version":2}'])
def test_invalid_authority_is_not_replaced_by_registration(
    consumer: Consumer, invalid: str
) -> None:
    _succeeded(consumer.register())
    authority = consumer.directory / "installation.json"
    authority.write_text(invalid, encoding="utf-8")
    before = authority.read_bytes()
    refused = consumer.register()
    assert refused.returncode != 0
    assert authority.read_bytes() == before
    shown = consumer.run("config", "show", "--json")
    assert shown.returncode != 0
    _assert_checkout_retained(consumer)


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux resource migration paths."
)
def test_interrupted_resource_migration_preserves_editable_ownership(
    consumer: Consumer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resume exact SDK resource inventory without changing the checkout runtime."""
    import apprc as rc
    from apprc.definition.installation import (
        InstallationPlacement,
        InventoryEntry,
        MigrationInventory,
    )
    from apprc.definition.paths import Layout, ResourceKind
    from apprc.user_files.app_home.writes import file_revision
    from apprc.user_files.installation.migration import resume_migration

    _succeeded(consumer.register())
    manager = rc.AppRC(
        app_id=consumer.name, paths=rc.Paths(config=True, appdata=True)
    ).installation(environment=consumer.environment)
    record = manager.inspect().record
    assert record is not None and record.active_runtime is not None
    runtime = record.active_runtime
    config, appdata = record.placement.config_dir, record.placement.appdata_dir
    assert config is not None and appdata is not None
    payload = appdata / "migration-payload.bin"
    payload.write_bytes(b"preserve application data")
    destination = tmp_path / "migrated resources"
    entries: list[InventoryEntry] = []
    targets: list[Path] = []
    roots: dict[ResourceKind, Path] = {"config": config, "appdata": appdata}
    for kind, root in roots.items():
        for source in sorted(root.rglob("*")):
            if source.is_dir():
                continue
            assert source.is_file() and not source.is_symlink()
            entries.append(InventoryEntry(source, "file", file_revision(source), kind))
            targets.append(destination / kind / source.relative_to(root))
    placement = InstallationPlacement(
        Layout.single_root(destination),
        config_dir=destination / "config",
        appdata_dir=destination / "appdata",
        capabilities=record.placement.capabilities,
    )
    plan = manager.plan_migration(
        placement,
        inventory=MigrationInventory(
            tmp_path, destination, tuple(entries), tuple(targets)
        ),
        quiescent=True,
    )
    original_rename = Path.rename

    def interrupt(source: Path, target: Path) -> Path:
        moved = original_rename(source, target)
        if source == payload:
            raise RuntimeError("interrupted after resource move")
        return moved

    monkeypatch.setattr(Path, "rename", interrupt)
    with pytest.raises(RuntimeError, match="interrupted after resource move"):
        manager.migrate(plan, quiescent=True)
    monkeypatch.setattr(Path, "rename", original_rename)
    pending = manager.inspect()
    assert pending.record is not None and pending.record.operation is not None
    assert pending.revision is not None
    assert pending.record.active_runtime == runtime
    unknown = appdata / "unlisted-user-content.txt"
    unknown.write_bytes(b"leave unlisted content untouched")
    resumed = resume_migration(
        consumer.directory,
        operation_id=pending.record.operation.operation_id,
        expected_revision=pending.revision,
    )
    assert resumed.record is not None
    assert resumed.record.status == "ready"
    assert resumed.record.operation is None
    assert resumed.record.placement == placement
    assert resumed.record.active_runtime == runtime
    assert (destination / "appdata" / payload.name).read_bytes() == (
        b"preserve application data"
    )
    assert unknown.read_bytes() == b"leave unlisted content untouched"
    _assert_checkout_retained(consumer)
    shown = consumer.run("config", "show", "--json")
    _succeeded(shown)
    assert str(destination / "config") in shown.stdout
