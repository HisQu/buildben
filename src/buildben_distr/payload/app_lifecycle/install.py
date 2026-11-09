"""Install this project through AppRC's bundled low-level runtime."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, cast
from uuid import uuid4

from apprc.definition.installation import (
    InstallationIdentity,
    InstallationInspection,
    InstallationPlacement,
    InstallationSource,
    MigrationInventory,
    OwnedOutput,
)
from apprc.definition.paths import Layout, Paths, ResourceKind
from apprc.distribution.models import AppCapabilities, DistributionSpec, ProjectMetadata
from apprc.distribution.runtime import (
    bind_install_support,
    execute_legacy_replacement,
    execute_migration,
    inspect_legacy_receipt,
    install_prepared_application,
    is_pending_legacy_replacement,
    parse_source_arguments,
    plan_legacy_replacement,
    SourceSelection,
    plan_migration,
    plan_repair,
    prepare_source,
    resume_legacy_replacement,
    resume_migration,
    stage_legacy_support,
)
from apprc.distribution.runtime.probe import probe_installed_tool
from apprc.distribution.runtime.backend import select_uv_target
from apprc.user_files.installation.discovery import (
    installation_directory,
    inspect_installation,
    native_user_directories,
)
from apprc.user_files.installation.operations import plan_install


def _bundle() -> dict[str, Any]:
    """Read the author inputs serialized by AppRC's standalone loader."""
    path = Path(sys.path[0]) / "apprc/distribution/runtime/bundle.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("app_id"), str):
        raise RuntimeError("Embedded application bundle has an unsupported schema.")
    return value


def _project_root(script: Path, distribution_path: PurePosixPath) -> Path:
    """Locate checkout from the generated entry path, never the caller CWD."""
    resolved = script.resolve()
    for candidate in resolved.parents:
        expected = candidate.joinpath(
            *distribution_path.parts, "artifacts", "installer", resolved.name
        )
        if (
            resolved.name in {"main-installer.py", "main-installer.pyz"}
            and expected.resolve() == resolved
        ):
            return candidate
    return resolved.parent


def _spec(bundle: dict[str, Any], script: Path) -> DistributionSpec:
    """Rebuild the standalone source contract without importing the app."""
    distribution_path = PurePosixPath(bundle["distribution_path"])
    identity = InstallationIdentity(
        app_id=bundle["app_id"],
        distribution=bundle["distribution"],
        import_package=bundle["import_package"],
        apprc_reference=bundle["apprc_reference"],
        commands=tuple(bundle["commands"]),
    )
    metadata = ProjectMetadata(
        project_root=_project_root(script, distribution_path),
        identity=identity,
        version=bundle["version"],
        project_path=PurePosixPath(bundle["project_path"]),
        distribution_path=distribution_path,
        launcher_command=bundle["launcher_command"],
        python_requirement=bundle["python_requirement"],
    )
    capabilities = AppCapabilities(
        paths=Paths(**bundle["paths"]),
        user_dotenv=bundle["user_dotenv"],
        workspaces=bundle["workspaces"],
        workspace_registry=bundle["workspace_registry"],
    )
    return DistributionSpec(
        metadata=metadata,
        capabilities=capabilities,
        source_mode=bundle["source_mode"],
        repository_url=bundle["repository_url"],
        release_version=bundle["release_version"],
        release_commit=bundle["release_commit"],
        release_asset=bundle["release_asset"],
        release_digest=bundle["release_digest"],
        runtime_requirements=tuple(bundle["runtime_requirements"]),
        runtime_overrides=tuple(bundle["runtime_overrides"]),
    )


def _placement(
    bundle: dict[str, Any],
    environment: dict[str, str],
    arguments: argparse.Namespace,
    inspection: InstallationInspection,
) -> InstallationPlacement:
    """Reuse saved absolute paths or capture an explicit first-install choice."""
    if (
        inspection.record is not None
        and arguments.layout is None
        and arguments.root is None
    ):
        return inspection.record.placement
    enabled = cast(dict[ResourceKind, bool], bundle["paths"])
    resource_kinds: tuple[ResourceKind, ...] = (
        "config",
        "appdata",
        "cache",
        "state",
    )
    if arguments.layout is None:
        if any(enabled.values()):
            if not sys.stdin.isatty():
                raise ValueError(
                    "Choose --layout native or --layout single-root --root PATH."
                )
            native = native_user_directories(bundle["app_id"], environment=environment)
            print("Native resource locations:")
            for name, path in zip(resource_kinds, native[:4], strict=True):
                actual = path / "appdata" if name == "appdata" else path
                if enabled[name]:
                    print(f"  {name}: {actual}")
            choice = input("Placement: [n]ative or [s]ingle-root? ").strip().casefold()
            if choice not in {"n", "s"}:
                raise ValueError("Choose native or single-root placement.")
            if choice == "s":
                arguments.layout = "single-root"
                arguments.root = Path(
                    input("Absolute root for enabled resources: ").strip()
                )
            else:
                arguments.layout = "native"
        else:
            arguments.layout = "native"
    roots: dict[ResourceKind, Path]
    if arguments.layout == "single-root":
        if arguments.root is None or not arguments.root.is_absolute():
            raise ValueError("--root must be absolute with --layout single-root")
        layout = Layout.single_root(arguments.root)
        roots = {name: arguments.root / name for name in resource_kinds}
        logs_dir = roots["state"] / "logs"
    else:
        if arguments.root is not None:
            raise ValueError("--root is allowed only with --layout single-root")
        layout = Layout.native()
        native = native_user_directories(bundle["app_id"], environment=environment)
        roots = dict(zip(resource_kinds, native[:4], strict=True))
        roots["appdata"] = roots["appdata"] / "appdata"
        logs_dir = native[4]
    paths: dict[ResourceKind, Path | None] = {
        name: roots[name] if enabled[name] else None for name in roots
    }
    return InstallationPlacement(
        layout=layout,
        config_dir=paths["config"],
        appdata_dir=paths["appdata"],
        cache_dir=paths["cache"],
        state_dir=paths["state"],
        logs_dir=logs_dir if enabled["state"] else None,
        capabilities=frozenset(name for name, value in enabled.items() if value),
    )


def _support_files(app_id: str) -> dict[PurePosixPath, bytes]:
    """Reuse verified owned support when a saved repair script is the entrypoint."""
    root = Path(sys.path[0]) / "app_lifecycle/_support"
    script = Path(sys.argv[0]).absolute()
    inspection = inspect_installation(script.parent, app_id=app_id)
    record = inspection.record
    if record is not None and any(
        output.kind == "support" and output.path == script.name
        for output in record.owned_outputs
    ):
        files: dict[PurePosixPath, bytes] = {}
        for output in record.owned_outputs:
            if output.kind != "support":
                continue
            relative = PurePosixPath(output.path)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or output.digest is None
            ):
                raise RuntimeError(
                    "Saved installation contains invalid support ownership."
                )
            path = script.parent.joinpath(*relative.parts)
            if path.is_symlink() or not path.is_file():
                raise RuntimeError(
                    f"Saved installation support is missing: {relative}."
                )
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != output.digest:
                raise RuntimeError(f"Saved installation support changed: {relative}.")
            files[relative] = content
        if files:
            return files
    if root.is_symlink() or root.parent.is_symlink() or not root.is_dir():
        raise RuntimeError(
            "Generated lifecycle support directory is missing or linked."
        )
    files: dict[PurePosixPath, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Generated lifecycle support contains a link: {path}.")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(
                f"Generated lifecycle support is not a regular file: {path}."
            )
        files[PurePosixPath(*path.relative_to(root).parts)] = path.read_bytes()
    if not files:
        raise RuntimeError("Generated lifecycle support is empty.")
    return files


def _legacy_directory(bundle: dict[str, Any], environment: dict[str, str]) -> Path:
    """Locate only the documented legacy Buildben state address."""
    if os.name == "nt":
        base = Path(environment["LOCALAPPDATA"])
    else:
        base_value = environment.get("XDG_STATE_HOME")
        base = (
            Path(base_value)
            if base_value
            else Path(environment.get("HOME", str(Path.home()))) / ".local" / "state"
        )
    distribution = re.sub(r"[-_.]+", "-", bundle["distribution"]).lower()
    if not base.is_absolute() or not distribution:
        raise ValueError("Legacy receipt location is not a valid native address.")
    return base / distribution / "installation"


def _resume_pending_migration(
    inspection: InstallationInspection,
) -> InstallationInspection:
    """Resume only the exact migration already recorded at this address."""
    record = inspection.record
    if record is None or record.migration is None or record.migration.cleanup_complete:
        return inspection
    if inspection.revision is None:
        raise RuntimeError("Pending migration has no authority revision.")
    operation_id = (
        record.operation.operation_id
        if record.operation is not None
        else record.migration.operation_id
    )
    if operation_id is None:
        raise RuntimeError("Pending migration has no recorded operation identity.")
    return resume_migration(
        inspection.directory,
        operation_id=operation_id,
        expected_revision=inspection.revision,
    )


def _validate_recovery_target(
    spec: DistributionSpec,
    inspection: InstallationInspection,
    arguments: argparse.Namespace,
    selection: SourceSelection,
) -> None:
    """Reject mismatched authority before any saved or external recovery."""
    # > Recovery may inspect pending authority that normal startup must reject.
    record = (
        inspection.record
        if inspection.status == "incomplete"
        else inspection.require_usable()
    )
    if record is None:
        raise RuntimeError("Saved repair requires installation authority.")
    target = (
        record.operation.intended
        if record.operation is not None and record.operation.intended is not None
        else record.current or record.last_successful
    )
    if target is None or target.identity != spec.metadata.identity:
        raise RuntimeError("Saved repair identity or snapshot is unavailable.")
    if (
        arguments.layout is not None
        and arguments.layout != target.placement.layout.mode
    ) or (
        arguments.root is not None and arguments.root != target.placement.layout.root
    ):
        raise RuntimeError("Recovery uses the recorded placement; it cannot relocate.")
    entry = Path(sys.argv[0]).absolute()
    if (
        entry.name in {"main-installer.py", "main-installer.pyz"}
        and arguments.repair
        and not is_pending_legacy_replacement(inspection)
        and not (
            inspection.record is not None and inspection.record.migration is not None
        )
        and not (
            selection.source.matches_observation(target.source)
            or target.source.matches_observation(selection.source)
        )
    ):
        raise RuntimeError("External repair source differs from captured authority.")


def _quiescence_recovery_command(directory: Path) -> str:
    """Render the exact saved or external repair command for fresh consent."""
    command = [
        sys.executable,
        str(Path(sys.argv[0]).absolute()),
        "--repair",
        "--directory",
        str(directory),
        "--legacy-quiescent",
    ]
    return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


def _resume_pending_legacy_replacement(
    spec: DistributionSpec,
    inspection: InstallationInspection,
    *,
    quiescent: bool,
    environment: dict[str, str],
) -> InstallationInspection:
    """Resume the recorded replacement using the SDK's retained inputs."""
    record = inspection.record
    if (
        record is None
        or record.operation is None
        or record.operation.intended is None
        or inspection.revision is None
    ):
        raise RuntimeError("Pending legacy replacement has no recorded target.")
    if not quiescent:
        raise RuntimeError(
            "Stop every legacy installer, launcher, and uninstaller, then run: "
            + _quiescence_recovery_command(inspection.directory)
        )
    return resume_legacy_replacement(
        inspection.directory,
        operation_id=record.operation.operation_id,
        expected_revision=inspection.revision,
        quiescent=quiescent,
        environment=environment,
        probe_path=Path(sys.path[0]) / "apprc/distribution/runtime/installed_probe.py",
        python_requirement=spec.metadata.python_requirement,
    )


def _migrate_legacy_receipt(
    bundle: dict[str, Any],
    spec: DistributionSpec,
    directory: Path,
    legacy_root: Path,
    placement: InstallationPlacement,
    source_file: Path,
    environment: dict[str, str],
    *,
    reinstall: bool = False,
) -> InstallationInspection:
    """Cut over validated legacy support through AppRC's public primitives."""
    legacy = inspect_legacy_receipt(
        legacy_root / "receipt.json",
        distribution=spec.metadata.identity.distribution,
        command=(
            "buildben"
            if spec.metadata.identity.distribution == "buildben"
            else spec.metadata.identity.commands[0]
        ),
    )
    if not legacy.compatible or legacy.receipt is None or legacy.backend is None:
        details = "; ".join(item.message for item in legacy.diagnostics)
        raise RuntimeError(
            details or "Legacy receipt is incomplete and cannot be migrated."
        )
    if legacy.version is None:
        raise RuntimeError("Legacy receipt does not identify an installed version.")
    evidence = json.loads(source_file.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict) or set(evidence) != {
        "source",
        "distribution_record_digest",
    }:
        raise ValueError(
            "Legacy evidence requires source and distribution_record_digest."
        )
    values = evidence["source"]
    if not isinstance(values, dict) or set(values) != {
        "kind",
        "requirement",
        "version",
        "digest",
        "runtime_requirements",
        "runtime_overrides",
    }:
        raise ValueError("Legacy evidence requires complete InstallationSource fields.")
    source = InstallationSource(
        kind=values["kind"],
        requirement=values["requirement"],
        version=values["version"],
        digest=values["digest"],
        runtime_requirements=tuple(values["runtime_requirements"]),
        runtime_overrides=tuple(values["runtime_overrides"]),
    )
    probe_path = Path(sys.path[0]) / "apprc/distribution/runtime/installed_probe.py"
    if reinstall:
        inspection = inspect_installation(directory, app_id=bundle["app_id"])
        replacement = plan_legacy_replacement(
            inspection,
            spec.metadata.identity,
            source,
            placement,
            legacy=legacy,
            inventory=MigrationInventory(
                source_root=directory, destination_root=directory
            ),
            expected_record_digest=evidence["distribution_record_digest"],
            quiescent=True,
        )
        with tempfile.TemporaryDirectory(prefix="apprc-source-") as staging:
            prepared = prepare_source(source, Path(staging).resolve())
            return execute_legacy_replacement(
                replacement,
                prepared,
                environment=environment,
                probe_path=probe_path,
                support_files=_support_files(bundle["app_id"]),
                python_requirement=spec.metadata.python_requirement,
            )
    observed = probe_installed_tool(
        legacy.backend,
        spec.metadata.identity,
        source,
        placement,
        probe_path=probe_path,
        environment=environment,
        expected_record_digest=evidence["distribution_record_digest"],
    )
    if observed.version != legacy.version:
        raise RuntimeError("Observed legacy package version differs from its receipt.")
    known = {"receipt.json", *(item.path.name for item in legacy.runnables)}
    inventory = MigrationInventory(
        source_root=legacy_root,
        destination_root=directory,
        unknown=tuple(path for path in legacy_root.iterdir() if path.name not in known),
    )
    if inventory.unknown:
        unknown = ", ".join(str(path) for path in inventory.unknown)
        raise RuntimeError(f"Legacy state contains unrecognized files: {unknown}")
    support_files = bind_install_support(
        _support_files(bundle["app_id"]), observed, directory
    )
    generation_id = uuid4()
    owned_outputs = tuple(
        OwnedOutput("support", str(relative), hashlib.sha256(content).hexdigest())
        for relative, content in sorted(support_files.items())
    )
    observed = dataclasses.replace(observed, owned_outputs=owned_outputs)
    staged = stage_legacy_support(
        directory,
        generation_id=generation_id,
        support_files={
            str(relative): content for relative, content in support_files.items()
        },
    )
    inspection = inspect_installation(directory, app_id=bundle["app_id"])
    plan = plan_migration(
        inspection,
        placement,
        inventory=inventory,
        quiescent=True,
        observed=observed,
        legacy=legacy.migration_evidence(),
        staged_support=staged,
        generation_id=generation_id,
    )
    return execute_migration(plan)


def main() -> int:
    """Acquire the selected immutable source and perform a managed install."""
    bundle = _bundle()
    spec = _spec(bundle, Path(sys.argv[0]).absolute())
    selection, remaining = parse_source_arguments(spec, sys.argv[1:])
    # > Resolve transport aliases; keep managed layout paths unchanged.
    if selection.package_path is not None:
        selection = dataclasses.replace(
            selection, package_path=selection.package_path.resolve(strict=True)
        )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", choices=("native", "single-root"))
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--migrate-legacy",
        action="store_true",
        help="Migrate the known legacy Buildben receipt after stopping old helpers.",
    )
    parser.add_argument(
        "--reinstall-legacy",
        action="store_true",
        help="Explicitly replace the legacy program from an immutable --legacy-source.",
    )
    parser.add_argument(
        "--legacy-quiescent",
        action="store_true",
        help="Confirm no legacy installer, launcher, or uninstaller is running.",
    )
    parser.add_argument(
        "--legacy-source",
        type=Path,
        help="JSON source plus independently observed old RECORD SHA-256; "
        "with --reinstall-legacy, source selects the immutable NEW package.",
    )
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--directory", type=Path)
    arguments = parser.parse_args(list(remaining))
    if arguments.reinstall_legacy and not arguments.migrate_legacy:
        parser.error("--reinstall-legacy requires --migrate-legacy.")
    if arguments.migrate_legacy and not arguments.legacy_quiescent:
        parser.error(
            "Legacy cutover requires --legacy-quiescent after stopping old helpers."
        )
    if arguments.migrate_legacy and arguments.layout is None:
        parser.error("Legacy cutover requires an explicit --layout choice.")
    saved_entry = Path(sys.argv[0]).absolute()
    if saved_entry.name == "repair-installer.py":
        arguments.repair = True
        if arguments.directory is None:
            arguments.directory = saved_entry.parent
    if arguments.repair and arguments.directory is None:
        parser.error("--repair requires --directory PATH.")
    if arguments.repair and (
        arguments.layout is not None or arguments.root is not None
    ):
        parser.error(
            "--repair uses saved placement; --layout and --root are not allowed."
        )
    if arguments.legacy_quiescent and not (
        arguments.migrate_legacy or arguments.repair
    ):
        parser.error("--legacy-quiescent requires --migrate-legacy or --repair.")
    environment = dict(os.environ)
    if arguments.repair:
        expected_directory = arguments.directory
        script = Path(sys.argv[0]).absolute()
        if (
            expected_directory is None
            or not expected_directory.is_absolute()
            or (
                script.name == "repair-installer.py"
                and script.parent.resolve() != expected_directory.resolve()
            )
            or script.name
            not in {"repair-installer.py", "main-installer.py", "main-installer.pyz"}
        ):
            raise RuntimeError(
                "Repair requires an absolute installation directory; saved repair "
                "must address its own parent."
            )
        directory = expected_directory
    else:
        directory = installation_directory(bundle["app_id"], environment=environment)
    inspection = inspect_installation(directory, app_id=bundle["app_id"])
    replacing_legacy = is_pending_legacy_replacement(inspection)
    recovering_migration = (
        inspection.record is not None
        and inspection.record.migration is not None
        and not inspection.record.migration.cleanup_complete
    )
    if arguments.repair or replacing_legacy or recovering_migration:
        _validate_recovery_target(spec, inspection, arguments, selection)
    if replacing_legacy:
        _resume_pending_legacy_replacement(
            spec,
            inspection,
            quiescent=arguments.legacy_quiescent,
            environment=environment,
        )
        return 0
    if (
        recovering_migration
        and inspection.record is not None
        and inspection.record.migration is not None
        and inspection.record.migration.legacy is not None
        and not arguments.legacy_quiescent
    ):
        raise RuntimeError(
            "Stop every legacy installer, launcher, and uninstaller, then run: "
            + _quiescence_recovery_command(inspection.directory)
        )
    inspection = _resume_pending_migration(inspection)
    saved = inspection.record
    if recovering_migration and arguments.migrate_legacy:
        return 0
    legacy_root = _legacy_directory(bundle, environment)
    legacy_receipt = legacy_root / "receipt.json"
    has_legacy_receipt = legacy_receipt.exists() or legacy_receipt.is_symlink()
    if has_legacy_receipt and saved is None:
        if inspection.status != "missing":
            raise RuntimeError(
                "Legacy receipt conflicts with invalid installation authority."
            )
        if not arguments.migrate_legacy:
            raise RuntimeError(
                "A legacy receipt requires explicit cutover with "
                "--migrate-legacy --legacy-quiescent --layout."
            )
        if not arguments.legacy_quiescent:
            parser.error(
                "Legacy cutover requires --legacy-quiescent after stopping old helpers."
            )
        if arguments.layout is None:
            parser.error("Legacy cutover requires an explicit --layout choice.")
        if arguments.legacy_source is None:
            parser.error(
                "Legacy cutover requires --legacy-source with source and old RECORD evidence."
            )
        placement = _placement(bundle, environment, arguments, inspection)
        inspection = _migrate_legacy_receipt(
            bundle,
            spec,
            directory,
            legacy_root,
            placement,
            arguments.legacy_source,
            environment,
            reinstall=arguments.reinstall_legacy,
        )
        return 0
    elif has_legacy_receipt:
        raise RuntimeError(
            "Legacy receipt remains beside managed authority; inspect migration "
            "state before continuing."
        )
    elif arguments.migrate_legacy and not recovering_migration:
        raise RuntimeError("No legacy receipt exists at the known native address.")
    prior = saved.current or saved.last_successful if saved is not None else None
    if arguments.repair:
        if saved is None:
            raise RuntimeError("Saved repair requires installation authority.")
        if saved.app_id != bundle["app_id"]:
            raise RuntimeError("Saved repair identity differs from this installer.")
        if saved.operation is not None:
            prior = saved.operation.intended
        if prior is None or prior.identity != spec.metadata.identity:
            raise RuntimeError("Saved repair identity or snapshot is unavailable.")
        selection = dataclasses.replace(selection, source=prior.source)
        placement = prior.placement
        backend = prior.backend
        plan = plan_repair(
            spec.metadata.identity,
            prior.source,
            placement,
            backend,
            inspection=inspection,
        )
    else:
        placement = _placement(bundle, environment, arguments, inspection)
        if prior is not None:
            backend = prior.backend
        else:
            selected_uv = environment.get("APPRC_UV_PATH") or environment.get("UV")
            if selected_uv:
                uv = Path(selected_uv)
                if not uv.is_absolute() or not uv.is_file():
                    raise RuntimeError(
                        "The bootstrap-selected absolute uv executable is unavailable."
                    )
                backend = select_uv_target(
                    uv, environment=environment, invocation_cwd=Path.cwd()
                )
            else:
                executable = shutil.which("uv")
                if executable is None:
                    raise RuntimeError("uv is required for managed installation")
                backend = select_uv_target(
                    Path(executable),
                    environment=environment,
                    invocation_cwd=Path.cwd(),
                )
        plan = plan_install(
            spec.metadata.identity,
            selection.source,
            placement,
            backend,
            inspection=inspection,
        )
    probe_path = Path(sys.path[0]) / "apprc/distribution/runtime/installed_probe.py"
    assert plan is not None
    with tempfile.TemporaryDirectory(prefix="apprc-source-") as staging:
        prepared = selection.prepare(Path(staging).resolve())
        install_prepared_application(
            plan,
            prepared,
            environment=environment,
            probe_path=probe_path,
            support_files=_support_files(bundle["app_id"]),
            python_requirement=spec.metadata.python_requirement,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
