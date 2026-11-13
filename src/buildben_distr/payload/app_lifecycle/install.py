"""Install this project through AppRC's bundled low-level runtime."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
import shutil
import sys
import tempfile
from collections.abc import Collection
from pathlib import Path, PurePosixPath

from apprc.definition.installation import (
    InstallationInspection,
    InstallationPlacement,
)
from apprc.definition.paths import Layout, ResourceKind
from apprc.distribution.models import DistributionSpec
from apprc.distribution.runtime import (
    SourceSelection,
    install_prepared_application,
    load_installer_spec,
    parse_source_arguments,
    plan_repair,
    prepare_installation_source,
    resume_migration,
)
from apprc.distribution.runtime.backend import select_uv_target
from apprc.user_files.installation.discovery import (
    installation_directory,
    inspect_installation,
    native_user_directories,
)
from apprc.user_files.installation.operations import plan_install


def _placement(
    spec: DistributionSpec,
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
    declared_paths = spec.capabilities.paths
    enabled: dict[ResourceKind, bool] = {
        "config": declared_paths.config,
        "appdata": declared_paths.appdata,
        "cache": declared_paths.cache,
        "state": declared_paths.state,
    }
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
            native = native_user_directories(
                spec.metadata.identity.app_id, environment=environment
            )
            print("Native resource locations:")
            for name, path in zip(resource_kinds, native[:4], strict=True):
                if enabled[name]:
                    actual = path / "appdata" if name == "appdata" else path
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
        native = native_user_directories(
            spec.metadata.identity.app_id, environment=environment
        )
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


def _support_files(
    app_id: str, *, exclude: Collection[PurePosixPath] = ()
) -> dict[PurePosixPath, bytes]:
    """Verify owned support except exact keys supplied by source preparation."""
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
            if relative in exclude:
                continue
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
        relative = PurePosixPath(*path.relative_to(root).parts)
        if relative not in exclude:
            files[relative] = path.read_bytes()
    if not files:
        raise RuntimeError("Generated lifecycle support is empty.")
    return files


def _resume_pending_migration(
    inspection: InstallationInspection,
) -> InstallationInspection:
    """Resume only a staged migration with matching current authority."""
    record = inspection.record
    if record is None or record.migration is None:
        return inspection
    if record.migration.phase == "activated":
        return inspection
    operation = record.operation
    if operation is None or operation.kind != "migrate":
        raise RuntimeError("Staged migration has no matching pending operation.")
    if inspection.revision is None:
        raise RuntimeError("Pending migration has no authority revision.")
    return resume_migration(
        inspection.directory,
        operation_id=operation.operation_id,
        expected_revision=inspection.revision,
    )


def _validate_recovery_target(
    spec: DistributionSpec,
    inspection: InstallationInspection,
    arguments: argparse.Namespace,
    selection: SourceSelection,
    *,
    check_source: bool = True,
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
        and check_source
        and arguments.repair
        and not (
            inspection.record is not None
            and inspection.record.migration is not None
            and inspection.record.migration.phase == "staged"
            and inspection.record.operation is not None
            and inspection.record.operation.kind == "migrate"
        )
        and not (
            selection.source.matches_observation(target.source)
            or target.source.matches_observation(selection.source)
        )
    ):
        raise RuntimeError("External repair source differs from captured authority.")


def main() -> int:
    """Acquire the selected immutable source and perform a managed install."""
    spec = load_installer_spec()
    app_id = spec.metadata.identity.app_id
    selection, remaining = parse_source_arguments(spec, sys.argv[1:])
    # > Resolve transport aliases; keep managed layout paths unchanged.
    if selection.package_path is not None:
        selection = dataclasses.replace(
            selection, package_path=selection.package_path.resolve(strict=True)
        )
    requested_selection = selection
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", choices=("native", "single-root"))
    parser.add_argument("--root", type=Path)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--directory", type=Path)
    arguments = parser.parse_args(list(remaining))
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
    environment = dict(os.environ)
    if arguments.repair:
        expected_directory = arguments.directory
        if (
            expected_directory is None
            or not expected_directory.is_absolute()
            or (
                Path(sys.argv[0]).absolute().name == "repair-installer.py"
                and Path(sys.argv[0]).absolute().parent.resolve()
                != expected_directory.resolve()
            )
            or Path(sys.argv[0]).absolute().name
            not in {
                "repair-installer.py",
                "main-installer.py",
                "main-installer.pyz",
            }
        ):
            raise RuntimeError(
                "Repair requires an absolute installation directory; saved repair "
                "must address its own parent."
            )
        directory = expected_directory
    else:
        directory = installation_directory(app_id, environment=environment)
    inspection = inspect_installation(directory, app_id=app_id)
    recovering_migration = (
        inspection.record is not None
        and inspection.record.migration is not None
        and inspection.record.migration.phase == "staged"
    )
    if arguments.repair or recovering_migration:
        _validate_recovery_target(
            spec, inspection, arguments, selection, check_source=False
        )
    inspection = _resume_pending_migration(inspection)
    saved = inspection.record
    prior = saved.current or saved.last_successful if saved is not None else None
    if arguments.repair:
        if saved is None:
            raise RuntimeError("Saved repair requires installation authority.")
        if saved.app_id != app_id:
            raise RuntimeError("Saved repair identity differs from this installer.")
        if saved.operation is not None:
            prior = saved.operation.intended
        if prior is None or prior.identity != spec.metadata.identity:
            raise RuntimeError("Saved repair identity or snapshot is unavailable.")
        selection = dataclasses.replace(selection, source=prior.source)
        placement = prior.placement
        backend = prior.backend
    else:
        placement = _placement(spec, environment, arguments, inspection)
        if prior is not None:
            backend = prior.backend
        else:
            selected_uv = environment.get("UV")
            if selected_uv is None:
                selected_uv = shutil.which("uv")
            if selected_uv is None:
                raise RuntimeError("uv is required for managed installation.")
            uv = Path(selected_uv)
            if not uv.is_absolute() or not uv.is_file():
                raise RuntimeError(
                    "The official UV handoff must name an available absolute executable."
                )
            backend = select_uv_target(
                uv, environment=environment, invocation_cwd=Path.cwd()
            )
    probe_path = Path(sys.path[0]) / "apprc/distribution/runtime/installed_probe.py"
    with tempfile.TemporaryDirectory(prefix="apprc-source-") as staging:
        prepared = prepare_installation_source(
            spec,
            selection,
            Path(staging).resolve(),
            repair_from=directory if arguments.repair else None,
        )
        if arguments.repair or recovering_migration:
            verified_selection = (
                dataclasses.replace(selection, source=prepared.source)
                if prepared.bundle is not None
                else requested_selection
            )
            _validate_recovery_target(spec, inspection, arguments, verified_selection)
        if arguments.repair:
            plan = plan_repair(
                spec.metadata.identity,
                prepared.source,
                placement,
                backend,
                inspection=inspection,
            )
        else:
            plan = plan_install(
                spec.metadata.identity,
                prepared.source,
                placement,
                backend,
                inspection=inspection,
            )
        install_prepared_application(
            plan,
            prepared,
            environment=environment,
            probe_path=probe_path,
            support_files=_support_files(
                app_id, exclude=(prepared.support_files or {}).keys()
            ),
            python_requirement=spec.metadata.runtime_python_requirement,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
